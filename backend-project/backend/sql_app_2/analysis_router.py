import logging.config
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, responses, Security, status
from sqlalchemy.orm import Session
import time, os, datetime, shutil, tempfile, zipfile, zoneinfo, asyncio, re
import pandas as pd

from . import crud, schemas
from .database import SessionLocal2, engine2

from .dependencies import wordcloud, sentence
from collections import Counter

from typing import Tuple, List, Annotated, Optional, Union, Literal
from datetime import timezone, timedelta
from contextlib import asynccontextmanager
import logging

# Dependency
def get_db():
    db = SessionLocal2()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(
    prefix="/analysis",
)

@router.post("/test_frequency", tags=["analysis"])
async def test_frequency(
    text: str = Form(...),
    lang: Literal['en', 'ja'] = Form('en'),
    db: Session = Depends(get_db)
):
    """
    Test the frequency analysis of a given text.
    """
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    # translate text if necessary
    translated_text = wordcloud.translate_text(text, target_lang=lang)
    
    # Calculate frequency
    frequency = wordcloud.cal_frequency(translated_text)
    
    return {
        "target_lang": lang,
        "original_text": text,
        "translated_text": translated_text,
        "frequency": frequency
    }

@router.get("/generations", tags=["analysis"], response_model=list[Tuple[schemas.GenerationAnalysis, schemas.RoundAnalysis]])
async def read_generations(
    program: Literal["none", "inlab_test","haga_sensei_test","student_january_experiment","student_1_sem_awe","student_1_sem_img"],
    db: Session = Depends(get_db)
):
    if program == "none":
        generations = crud.get_generations(
            db,
            limit=10000,
        )
        return generations
    program = crud.get_program_by_name(db, program)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    generations = crud.get_generations(
        db, 
        program_id=program.id,
        limit=10000,
    )

    return generations

def get_frequency(
        cloud_type: Literal['mistake', 'writing', 'user_chat', 'assistant_chat'],
        db_generations_rounds,
        lang: Literal['ja', 'en'] = 'en',
        latest_generation_msg_id: int = 0
):
    max_message_id = 0
    frequencies = []
    generation_token = {}
    if cloud_type == 'mistake':
        
        for db_generation, db_round in db_generations_rounds:
            
            if db_generation.id <= latest_generation_msg_id:
                continue
            if db_generation.grammar_errors:
                grammar_errors = wordcloud.translate_text(
                    text=' '.join([grammar_error.explanation for grammar_error in sentence.str_to_list(db_generation.grammar_errors)]),
                    target_lang=lang,
                )
                
                frequency = wordcloud.cal_frequency(
                    text=grammar_errors,
                    lang=lang,
                )
                generation_token[db_generation.id] = frequency
                frequencies.append(frequency)
            if db_generation.spelling_errors:
                spelling_errors = wordcloud.translate_text(
                    text=' '.join([spelling_error.correction for spelling_error in sentence.str_to_list(db_generation.spelling_errors)]),
                    target_lang=lang,
                )
                
                frequency = wordcloud.cal_frequency(
                    text=spelling_errors,
                    lang=lang,
                )
                generation_token[db_generation.id]={**generation_token[db_generation.id], **frequency}
                frequencies.append(frequency)

    elif cloud_type == 'writing':

        for db_generation, db_round in db_generations_rounds:
            if db_generation.id <= latest_generation_msg_id:
                continue
            frequency = wordcloud.cal_frequency(
                text=db_generation.sentence,
                lang=lang,
            )
            generation_token[db_generation.id] = frequency
            frequencies.append(frequency)
    elif cloud_type == 'user_chat':

        for round in db_generations_rounds:
            for msg in round.chat.messages:
                if msg.id <= latest_generation_msg_id:
                    continue
                
                if msg.sender == 'user':
                    max_message_id = max([max_message_id, msg.id])
                    msg_content = wordcloud.translate_text(
                        text=msg.content.replace('\n', ''),
                        target_lang=lang,
                    )
                    frequency = wordcloud.cal_frequency(
                        text=msg_content,
                        lang=lang,
                    )
                    generation_token[msg.id] = frequency
                    frequencies.append(frequency)
    elif cloud_type == 'assistant_chat':

        for round in db_generations_rounds:
            for msg in round.chat.messages:
                if msg.id <= latest_generation_msg_id:
                    continue
                if not (msg.is_hint or msg.is_evaluation):
                    continue
                if msg.sender == 'assistant':
                    max_message_id = max([max_message_id, msg.id])
                    msg_content = wordcloud.translate_text(
                        text=msg.content.replace('\n', ''),
                        target_lang=lang,
                    )
                    frequency = wordcloud.cal_frequency(
                        text=msg_content,
                        lang=lang,
                    )
                    generation_token[msg.id] = frequency
                    frequencies.append(frequency)
    sum_frequency = sum((Counter(freq) for freq in frequencies), Counter())

    max_generation_id = db_generations_rounds[0][0].id if '_chat' not in cloud_type else None
    output = {
        'frequency': sum_frequency,
        'max_generation_id': max_generation_id,
        'max_message_id': max_message_id,
        'generation_token': generation_token
    }
    return output

@router.get("/leaderboards/{leaderboard_id}/{program_name}", tags=["analysis"])
async def read_word_cloud(
    leaderboard_id: int,
    program_name: Literal["none", "inlab_test","haga_sensei_test","student_january_experiment","student_1_sem_awe","student_1_sem_img"],
    cloud_type: Literal['mistake', 'writing', 'user_chat', 'assistant_chat'] = 'mistake',
    lang: Literal['ja', 'en'] = 'en',
    db: Session = Depends(get_db)
):
    """
    Get the leaderboard analysis for a specific program.
    """
    db_program = crud.get_program_by_name(db, program_name)
    
    # Check if word cloud exists
    if not db_program:
        raise HTTPException(status_code=404, detail="Program not found")
    db_leaderboard_analysis = crud.read_leaderboard_analysis(
        db=db,
        leaderboard_id=leaderboard_id,
        program_id=db_program.id,
    )
    if not db_leaderboard_analysis:
        db_leaderboard_analysis = crud.create_leaderboard_analysis(
            db=db,
            leaderboard_analysis=schemas.LeaderboardAnalysisCreate(
                program_id=db_program.id,
                leaderboard_id=leaderboard_id,
            )
        )

    # Check if generations exist for the leaderboard and program
    # If not, no need to create a new word cloud
    db_generations = crud.get_generations(
        db=db,
        program_id=db_program.id,
        leaderboard_id=leaderboard_id,
        limit=10000,
    )

    if not db_generations and '_chat' not in cloud_type:
        raise HTTPException(status_code=404, detail="No generations found for the leaderboard and program")

    # Check if rounds exist for the leaderboard and program
    # If not, no need to create a new word cloud
    db_rounds = crud.get_rounds(
        db=db,
        leaderboard_id=leaderboard_id,
        program_id=db_program.id,
        limit=10000,
    )
    if not db_rounds:
        raise HTTPException(status_code=404, detail="No rounds found for the leaderboard and program")

    db_leaderboard_wordcloud = crud.read_leaderboard_analysis_word_cloud(
        db=db,
        leaderboard_analysis_id=db_leaderboard_analysis.id,
        cloud_type=cloud_type,
        lang=lang,
        require_num=1
    )

    descriptions = crud.get_description(db, leaderboard_id=leaderboard_id)
    description_frequency = wordcloud.cal_frequency(
        text=' '.join([des.content for des in descriptions]),
        lang='en'
    )

    if db_leaderboard_wordcloud:
        # Calculate frequency of each word
        db_word_cloud = crud.read_word_cloud(
            db=db,
            id=db_leaderboard_wordcloud.word_cloud_id,
        )

        # Check if new generation before updating word cloud
        if cloud_type in ['writing', 'mistake'] and db_word_cloud.latest_generation_id < db_generations[0][0].id:
            generations_frequency = crud.get_generations(db=db, program_id=db_program.id, leaderboard_id=leaderboard_id, skip=db_word_cloud.latest_generation_id)
            dict_frequency = get_frequency(
                cloud_type=cloud_type,
                generations=generations_frequency,
                lang=lang,
                latest_generation_msg_id=db_word_cloud.latest_generation_id
            )

            items = [schemas.WordCloudItemCreate(
                word=word,
                frequency=count,
                color="959695" if word in description_frequency else "ffffff"
            ) for word, count in dict_frequency['frequency'].items()]

            # Update the word cloud with new items
            word_cloud_update = schemas.WordCloudUpdate(
                id=db_word_cloud.id,
                last_updated=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
                latest_generation_id=dict_frequency['max_message_id'] if '_chat' in cloud_type else dict_frequency['max_generation_id'],
                items=items,
            )

            db_word_cloud = crud.update_word_cloud(
                db=db,
                cloud_type=cloud_type,
                word_cloud=word_cloud_update,
            )

            for gen in dict_frequency['generation_token']:
                for dict_word, count in dict_frequency['generation_token'][gen].items():
                    word_cloud_item = crud.get_word_cloud_item_by_word(
                        db=db,
                        word=dict_word,
                        word_cloud_id=db_word_cloud.id,
                        cloud_type=cloud_type
                    )
                    crud.create_word_cloud_item_generation(
                    db=db,
                    cloud_type=cloud_type,
                    word_cloud_item_id=word_cloud_item.id,
                    generation_or_message_id=gen
                    )
        elif cloud_type in ['user_chat', 'assistant_chat']:
            tokyo_tz = zoneinfo.ZoneInfo("Asia/Tokyo")
            current_time = datetime.datetime.now(tz=tokyo_tz)
            if db_word_cloud.last_updated.tzinfo is None:
                db_word_cloud.last_updated = db_word_cloud.last_updated.replace(tzinfo=tokyo_tz)
            
            # Only update if the last updated time is more than 1 minute ago
            if db_word_cloud.last_updated < current_time - timedelta(minutes=1):
                dict_frequency = get_frequency(
                    cloud_type=cloud_type,
                    db_generations_rounds=db_rounds,
                    lang=lang,
                    latest_generation_msg_id=db_word_cloud.latest_generation_id
                )

                items = [
                    schemas.WordCloudItemCreate(
                        word=word,
                        frequency=count,
                        color="959695" if word in description_frequency else "ffffff"
                    ) for word, count in dict_frequency['frequency'].items()
                ]

                # Update the word cloud with new items
                word_cloud_update = schemas.WordCloudUpdate(
                    id=db_word_cloud.id,
                    last_updated=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
                    latest_generation_id=dict_frequency['max_message_id'] if '_chat' in cloud_type else dict_frequency['max_generation_id'],
                    items=items,
                )

                db_word_cloud = crud.update_word_cloud(
                    db=db,
                    cloud_type=cloud_type,
                    word_cloud=word_cloud_update,
                )

                for msg in dict_frequency['generation_token']:
                    for dict_word, count in dict_frequency['generation_token'][msg].items():
                        word_cloud_item = crud.get_word_cloud_item_by_word(
                            db=db,
                            word=dict_word,
                            word_cloud_id=db_word_cloud.id,
                            cloud_type=cloud_type
                        )
                        crud.create_word_cloud_item_generation(
                            db=db,
                            cloud_type=cloud_type,
                            word_cloud_item_id=word_cloud_item.id,
                            generation_or_message_id=msg
                        )
            
        db_leaderboard_analysis = crud.read_leaderboard_analysis(
            db=db,
            leaderboard_id=leaderboard_id,
            program_id=db_program.id,
        )
    elif cloud_type in ['writing', 'mistake']:
        dict_frequency = get_frequency(
            cloud_type=cloud_type,
            db_generations_rounds=db_generations,
            lang=lang,
            latest_generation_msg_id=0
        )
        items = [
            schemas.WordCloudItemCreate(
                word=word,
                frequency=count,
                color="959695" if word in description_frequency else "ffffff"
            ) for word, count in dict_frequency['frequency'].items()
        ]

        # Create the word cloud
        db_word_cloud = crud.create_word_cloud(
            db=db,
            cloud_type=cloud_type,
            word_cloud=schemas.WordCloudCreate(
                last_updated=datetime.datetime.now(
                    tz=zoneinfo.ZoneInfo("Asia/Tokyo")
                ),
                latest_generation_id=dict_frequency['max_generation_id'],
                items=items,
            )
        )

        for gen in dict_frequency['generation_token']:
            for dict_word, count in dict_frequency['generation_token'][gen].items():
                word_cloud_item = crud.get_word_cloud_item_by_word(
                    db=db,
                    word=dict_word,
                    word_cloud_id=db_word_cloud.id,
                    cloud_type=cloud_type
                )
                crud.create_word_cloud_item_generation(
                    db=db,
                    cloud_type=cloud_type,
                    word_cloud_item_id=word_cloud_item.id,
                    generation_or_message_id=gen
                )

        db_leaderboard_wordcloud = crud.create_leaderboard_analysis_word_cloud(
            db=db,
            leaderboard_analysis_word_cloud=schemas.LeaderboardAnalysis_WordCloudCreate(
                leaderboard_analysis_id=db_leaderboard_analysis.id,
                word_cloud_id=db_word_cloud.id,
                type=cloud_type,
                lang=lang,
            )
        )
    elif cloud_type in ['user_chat', 'assistant_chat']:
        dict_frequency = get_frequency(
            cloud_type=cloud_type,
            db_generations_rounds=db_rounds,
            lang=lang,
            latest_generation_msg_id=0
        )
        items = [
            schemas.WordCloudItemCreate(
                word=word,
                frequency=count,
                color="959695" if word in description_frequency else "ffffff"
            ) for word, count in dict_frequency['frequency'].items()
        ]

        # Create the word cloud
        db_word_cloud = crud.create_word_cloud(
            db=db,
            cloud_type=cloud_type,
            word_cloud=schemas.WordCloudCreate(
                last_updated=datetime.datetime.now(
                    tz=zoneinfo.ZoneInfo("Asia/Tokyo")
                ),
                latest_generation_id=dict_frequency['max_message_id'],
                items=items,
            )
        )

        for msg in dict_frequency['generation_token']:
            for dict_word, count in dict_frequency['generation_token'][msg].items():
                word_cloud_item = crud.get_word_cloud_item_by_word(
                    db=db,
                    word=dict_word,
                    word_cloud_id=db_word_cloud.id,
                    cloud_type=cloud_type
                )
                crud.create_word_cloud_item_generation(
                    db=db,
                    cloud_type=cloud_type,
                    word_cloud_item_id=word_cloud_item.id,
                    generation_or_message_id=msg
                )

        db_leaderboard_wordcloud = crud.create_leaderboard_analysis_word_cloud(
            db=db,
            leaderboard_analysis_word_cloud=schemas.LeaderboardAnalysis_WordCloudCreate(
                leaderboard_analysis_id=db_leaderboard_analysis.id,
                word_cloud_id=db_word_cloud.id,
                type=cloud_type,
                lang=lang,
            )
        )
    
    db_leaderboard = crud.get_leaderboard(
        db=db,
        leaderboard_id=leaderboard_id
    )

    mistake_word_cloud = crud.read_leaderboard_analysis_word_cloud(
                            db=db,
                            leaderboard_analysis_id=db_leaderboard_analysis.id,
                            cloud_type='mistake',
                            lang=lang,
                            require_num=1
                        )
    if mistake_word_cloud:
        mistake_word_cloud_id = mistake_word_cloud.word_cloud_id
    else:
        mistake_word_cloud_id = None

    writing_word_cloud = crud.read_leaderboard_analysis_word_cloud(
                            db=db,
                            leaderboard_analysis_id=db_leaderboard_analysis.id,
                            cloud_type='writing',
                            lang=lang,
                            require_num=1
                        )
    if writing_word_cloud:
        writing_word_cloud_id = writing_word_cloud.word_cloud_id
    else:
        writing_word_cloud_id = None

    user_chat_word_cloud = crud.read_leaderboard_analysis_word_cloud(
        db=db,
        leaderboard_analysis_id=db_leaderboard_analysis.id,
        cloud_type='user_chat',
        lang=lang,
        require_num=1
    )
    
    if user_chat_word_cloud:
        
        user_chat_word_cloud_id = user_chat_word_cloud.word_cloud_id
    else:
        user_chat_word_cloud_id = None

    assistant_chat_word_cloud = crud.read_leaderboard_analysis_word_cloud(
        db=db,
        leaderboard_analysis_id=db_leaderboard_analysis.id,
        cloud_type='assistant_chat',
        lang=lang,
        require_num=1
    )
    
    if assistant_chat_word_cloud:
        
        assistant_chat_word_cloud_id = assistant_chat_word_cloud.word_cloud_id
    else:
        assistant_chat_word_cloud_id = None

    return schemas.LeaderboardAnalysis(
        id=db_leaderboard_analysis.id,
        title=db_leaderboard.title,
        story_extract=db_leaderboard.story_extract,
        published_at=db_leaderboard.published_at,
        descriptions=[des.content for des in descriptions],
        mistake_word_cloud_id=mistake_word_cloud_id,
        writing_word_cloud_id=writing_word_cloud_id,
        user_chat_word_cloud_id=user_chat_word_cloud_id,
        assistant_chat_word_cloud_id=assistant_chat_word_cloud_id,
    )

@router.delete("/word_cloud/{word_cloud_id}", tags=["analysis"])
async def delete_word_cloud(
    word_cloud_id: int,
    db: Session = Depends(get_db)
):
    word_cloud = crud.delete_word_cloud(
        db=db,
        id=word_cloud_id
    )

    if not word_cloud:
        raise HTTPException(status_code=404, detail="Word cloud not found")
    
    return responses.JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Word cloud deleted successfully"}
    )

@router.post("/get_word_cloud_items", tags=["analysis"], response_model=list[Union[schemas.WordCloudItemAnalysis, schemas.ChatWordCloudAnalysis]])
async def get_word_cloud_items(
    word_cloud_id: int,
    cloud_type: Literal['mistake', 'writing', 'user_chat', 'assistant_chat'],
    db: Session = Depends(get_db)
):
    if cloud_type == 'mistake':
        mistake_word_cloud_items = [
            schemas.WordCloudItemAnalysis(
                id=item.id,
                word=item.word,
                frequency=item.frequency,
                color=item.color,
                generations=[
                    schemas.GenerationItemAnalysis(
                        id=gen.id,
                        user=schemas.UserAnalysis(
                            id=gen.round.player.id,
                            profiles=schemas.UserProfileOut(
                                display_name=gen.round.player.display_name,
                            )
                        ),
                        round_id=gen.round_id,
                        sentence=gen.sentence,
                        correct_sentence=gen.correct_sentence,
                        mistakes=[
                            schemas.MistakeItemAnalysis(
                                **vars(mistake)
                            ) for mistake in sentence.str_to_list(gen.grammar_errors)
                        ]+
                        [
                            schemas.MistakeItemAnalysis(
                                extracted_text=mistake['word'],
                                correction=mistake['correction'],
                                explanation=''
                            ) for mistake in sentence.str_to_list(gen.spelling_errors)
                        ]
                    ) 
                    for gen in crud.get_generations_by_ids(
                        db=db,
                        generation_ids=[
                            k.generation_id
                            for k in
                            crud.get_word_cloud_item_generation(
                            db=db,
                            cloud_type='mistake',
                            word_cloud_item_id=item.id)
                        ]
                    )
                ]
            )
            for item in crud.read_word_cloud(
                    db=db,
                    id=word_cloud_id
                ).mistake_word_cloud_items
        ]
        return mistake_word_cloud_items
    elif cloud_type == 'writing':
        writing_word_cloud_items = [
            schemas.WordCloudItemAnalysis(
                id=item.id,
                word=item.word,
                frequency=item.frequency,
                color=item.color,
                generations=[
                    schemas.GenerationItemAnalysis(
                        id=gen.id,
                        user=schemas.UserAnalysis(
                            id=gen.round.player.id,
                            profiles=schemas.UserProfileOut(
                                display_name=gen.round.player.display_name,
                            )
                        ),
                        round_id=gen.round_id,
                        sentence=gen.sentence,
                        correct_sentence=gen.correct_sentence,
                        mistakes=[]
                    ) for gen in crud.get_generations_by_ids(
                        db=db,
                        generation_ids=[
                            k.generation_id
                            for k in
                            crud.get_word_cloud_item_generation(
                                db=db,
                                cloud_type='writing',
                                word_cloud_item_id=item.id)]
                        )
                ]
            )
            for item in crud.read_word_cloud(
                    db=db,
                    id=word_cloud_id
                ).writing_word_cloud_items
        ]
        return writing_word_cloud_items
    elif cloud_type == 'user_chat':
        user_chat_word_cloud_items = [
            schemas.ChatWordCloudAnalysis(
                id=item.id,
                word=item.word,
                frequency=item.frequency,
                color=item.color,
                chat_messages=[
                    schemas.ChatMessageAnalysis(
                        id=msg.id,
                        chat_id=msg.chat_id,
                        sender=msg.sender,
                        content=msg.content,
                        created_at=msg.created_at,
                    )
                    for msg in crud.get_chat_messages_by_ids(
                        db=db,
                        message_ids=[
                            k.message_id
                            for k in
                            crud.get_word_cloud_item_generation(
                                db=db,
                                cloud_type='user_chat',
                                word_cloud_item_id=item.id
                            )
                        ]
                    )
                ]
            )
            for item in crud.read_word_cloud(
                    db=db,
                    id=word_cloud_id
                ).user_chat_word_cloud_items
        ]
        return user_chat_word_cloud_items
    elif cloud_type == 'assistant_chat':
        assistant_chat_word_cloud_items = [
            schemas.ChatWordCloudAnalysis(
                id=item.id,
                word=item.word,
                frequency=item.frequency,
                color=item.color,
                chat_messages=[
                    schemas.ChatMessageAnalysis(
                        id=msg.id,
                        chat_id=msg.chat_id,
                        sender=msg.sender,
                        content=msg.content,
                        created_at=msg.created_at,
                    )
                    for msg in crud.get_chat_messages_by_ids(
                        db=db,
                        message_ids=[
                            k.message_id
                            for k in
                            crud.get_word_cloud_item_generation(
                                db=db,
                                cloud_type='assistant_chat',
                                word_cloud_item_id=item.id
                            )
                        ]
                    )
                ]
            )
            for item in crud.read_word_cloud(
                    db=db,
                    id=word_cloud_id
                ).assistant_chat_word_cloud_items
        ]
        return assistant_chat_word_cloud_items
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cloud type"
        )

@router.post("/word_cloud/{word_cloud_item_id}/color")
async def update_word_cloud_item_color(
        word_cloud_item_id: int,
        color: str,
        cloud_type: Literal['mistake', 'writing', 'user_chat', 'assistant_chat'],
        db: Session = Depends(get_db)
):
    """
    Update the color of a word cloud item.
    """

    # check whether color is 6-character hex color code
    hex_color_pattern = re.compile(r'^#?[0-9a-fA-F]{6}$')

    check_color = hex_color_pattern.match(color)
    if check_color:
        # Remove leading '#' if present
        color = color.lstrip('#')
        
        updated_word_cloud_item = crud.update_word_cloud_item_color(
            db=db,
            word_cloud_item_id=word_cloud_item_id,
            color=color
        )
        
        return updated_word_cloud_item
    
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid color format"
    )