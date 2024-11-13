from fastapi import Depends, FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks, responses
from sqlalchemy.orm import Session
import shutil, time, os, datetime, io, requests
from pathlib import Path
from PIL import Image

from . import crud, models, schemas
from .database import SessionLocal, engine

from .dependencies import sentence, gen_image, score, dictionary, openai_chatbot

from typing import Union, List, Annotated, Optional
from datetime import timezone

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Define the directory where the images will be stored
media_dir = Path(os.getenv("MEDIA_DIR", "/static"))
media_dir.mkdir(parents=True, exist_ok=True)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generateDescription(db: Session, leaderboard_id: int, image: str, story: Optional[str], model_name: str="gpt-4o-mini"):
    
    contents = sentence.genSentences(
        image=image,
        story=story
    )

    db_descriptions = []

    for content in contents:
        d = schemas.DescriptionBase(
            content=content,
            model=model_name,
            leaderboard_id=leaderboard_id
        )
        
        db_description = crud.create_description(
            db=db,
            description=d
        )
        
        db_descriptions.append(db_description)
    
    db_leaderboard = crud.update_leaderboard_difficulty(
        db=db,
        leaderboard_id=leaderboard_id,
        difficulty_level=len(contents)
    )

    return db_descriptions

def calculate_score(
    db: Session,
    generation: schemas.GenerationCompleteCreate,
    is_completed: bool=False
):
    
    db_generation = crud.get_generation(db, generation_id=generation.id)
    if db_generation is None:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    if db_generation.duration==0 or db_generation.total_score==0:
        db_round = crud.get_round(db, round_id=db_generation.round_id)
        ai_play = crud.get_description(db, leaderboard_id=db_round.leaderboard_id, model_name=db_round.model)

        if not ai_play:
            story_path=db_round.leaderboard.story.textfile_path
            story=Path(story_path).read_text()
            
            ai_play = generateDescription(
                db=db,
                leaderboard_id=db_round.leaderboard_id, 
                image=str(db_round.leaderboard.original_image.image_path), 
                story=story, 
                model_name="gpt-4o-mini"
            )

        factors, scores=score.calculate_score_init(
            image_path=db_round.leaderboard.original_image.image_path,
            sentence=db_generation.sentence,
        )

        if is_completed:
            generation_aware = generation.at.replace(tzinfo=timezone.utc)
            db_generation_aware = db_generation.created_at.replace(tzinfo=timezone.utc)
            duration = (generation_aware - db_generation_aware).seconds
        else: 
            duration = 0

        generation_com = schemas.GenerationComplete(
            id=db_round.id,
            n_words=factors['n_words'],
            n_conjunctions=factors['n_conjunctions'],
            n_adj=factors['n_adj'],
            n_adv=factors['n_adv'],
            n_pronouns=factors['n_pronouns'],
            n_prepositions=factors['n_prepositions'],

            n_grammar_errors=factors['n_grammar_errors'],
            n_spelling_errors=factors['n_spelling_errors'],

            perlexity=factors['perplexity'],

            f_word=factors['f_word'],
            f_bigram=factors['f_bigram'],

            n_clauses=factors['n_clauses'],

            content_score=scores['content_score'],

            total_score=scores['total_score'],
            rank=score.rank(scores['total_score']),
            duration=duration,
            is_completed=is_completed
        )

    else:

        generation_aware = generation.at.replace(tzinfo=timezone.utc)
        db_generation_aware = db_generation.created_at.replace(tzinfo=timezone.utc)
        duration = (generation_aware - db_generation_aware).seconds

        generation_com = schemas.GenerationComplete(
            id=db_generation.id,
            
            n_words=db_generation.n_words,
            n_conjunctions=db_generation.n_conjunctions,
            n_adj=db_generation.n_adj,
            n_adv=db_generation.n_adv,
            n_pronouns=db_generation.n_pronouns,
            n_prepositions=db_generation.n_prepositions,

            n_grammar_errors=db_generation.n_grammar_errors,
            n_spelling_errors=db_generation.n_spelling_errors,

            perlexity=db_generation.perlexity,

            f_word=db_generation.f_word,
            f_bigram=db_generation.f_bigram,

            n_clauses=db_generation.n_clauses,

            content_score=db_generation.content_score,

            rank=db_generation.rank,
            duration=duration,
            is_completed=is_completed
        )

        factors = {
            'n_words': db_generation.n_words,
            'n_conjunctions': db_generation.n_conjunctions,
            'n_adj': db_generation.n_adj,
            'n_adv': db_generation.n_adv,
            'n_pronouns': db_generation.n_pronouns,
            'n_prepositions': db_generation.n_prepositions,
            'n_grammar_errors': db_generation.n_grammar_errors,
            'n_spelling_errors': db_generation.n_spelling_errors,
            'perplexity': db_generation.perlexity,
            'f_word': db_generation.f_word,
            'f_bigram': db_generation.f_bigram,
            'n_clauses': db_generation.n_clauses,
            'content_score': db_generation.content_score
        }

        scores = score.calculate_score(**factors)

    crud.update_generation3(
        db=db,
        generation=generation_com
    )

    return factors, scores

def update_vocab_used_time(
        db: Session,
        sentence: str,
        user_id: int,
):
    updated_vocab = []
    doc = dictionary.get_sentence_nlp(sentence)
    for token in doc:
        db_vocab = crud.get_vocabulary(
            db=db,
            vocabulary=token.lemma_,
            part_of_speech=token.pos_
        )
        if db_vocab:
            db_personal_dictionary = crud.get_personal_dictionary(
                db=db,
                player_id=user_id,
                vocabulary_id=db_vocab.id
            )

            if db_personal_dictionary:
                updated_vocab.append(
                    crud.update_personal_dictionary_used(
                        db=db,
                        dictionary=schemas.PersonalDictionaryId(
                            player=user_id,
                            vocabulary=db_vocab
                        )
                    )
                )
    return updated_vocab
            

@app.post("/users/", tags=["User"], response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@app.delete("/users/{user_id}", tags=["User"], response_model=schemas.UserBase)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return crud.delete_user(db=db, user_id=user_id)

@app.get("/users/", tags=["User"], response_model=list[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", tags=["User"], response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/scenes/", tags=["Scene"], response_model=list[schemas.Scene])
def read_scenes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    scenes = crud.get_scenes(db, skip=skip, limit=limit)
    return scenes

@app.post("/scene/", tags=["Scene"], response_model=schemas.Scene)
def create_scene(scene: schemas.SceneBase, db: Session = Depends(get_db)):
    return crud.create_scene(db=db, scene=scene)

@app.get("/stories/", tags=["Story"], response_model=list[schemas.StoryOut])
def read_stories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    stories = crud.get_stories(db, skip=skip, limit=limit)
    return stories

@app.post("/story/", tags=["Story"], response_model=schemas.StoryOut)
def create_story(
    story_content_file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    scene_id: Annotated[int, Form()],
    db: Session = Depends(get_db),
):
    if not os.path.exists(media_dir / "stories"):
        raise HTTPException(status_code=400, detail="The directory for stories does not exist")
    if not story_content_file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Please upload a text file")
    
    timestamp = str(int(time.time()))
    shortenfilename=".".join(story_content_file.filename.split(".")[:-1])[:20]
    fileattr = story_content_file.filename.split(".")[-1:][0]
    filename = f"s_{timestamp}_{shortenfilename}.{fileattr}"
    textfile_path = media_dir / "stories" / filename
    
    try:
        story_content = story_content_file.file.read()
        if not os.path.isfile(textfile_path):
            with open(textfile_path, "wb") as f:
                f.write(story_content)
                
    except Exception:
        return {"message": f"There was an error uploading the file\n{Exception}"}
    finally:
        story_content_file.file.close()

    storyCreate = schemas.StoryCreate(
        title=title,
        scene_id=scene_id,
        textfile_path=str(textfile_path)
    )

    return crud.create_story(db=db, story=storyCreate)


@app.get("/leaderboards/", tags=["Leaderboard"], response_model=list[schemas.LeaderboardOut])
def read_leaderboards(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    leaderboards = crud.get_leaderboards(db, skip=skip, limit=limit)
    return leaderboards

@app.post("/leaderboards/", tags=["Leaderboard"], response_model=schemas.LeaderboardOut)
def create_leaderboard(
    original_image: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    story_extract: Annotated[str, Form()],
    is_public: Annotated[bool, Form()],
    scene_id: Annotated[int, Form()],
    story_id: Annotated[int, Form()],
    user_id: Annotated[int, Form()],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    
    timestamp = str(int(time.time()))
    shortenfilename=".".join(original_image.filename.split(".")[:-1])[:20]
    fileattr = original_image.filename.split(".")[-1:][0]
    filename = f"o_{timestamp}_{shortenfilename}.{fileattr}"
    image_path = media_dir / "original_images" / filename

    try:
        image_content = Image.open(original_image.file)
    except Exception:
        raise HTTPException(status_code=400, detail="Please upload a valid image file")

    try:
        if not os.path.isfile(image_path):
            image_content.save(image_path)
    except Exception:
        raise HTTPException(status_code=400, detail="There was an error uploading the file")
    finally:
        original_image.file.close()
        
    db_original_image = crud.create_original_image(
        db=db,
        image=schemas.ImageBase(
            image_path=str(image_path),
        )
    )

    if story_id==0:
        story_id=None

    db_leaderboard = schemas.LeaderboardCreate(
        title=title,
        story_extract=story_extract,
        is_public=is_public,
        scene_id=scene_id,
        story_id=story_id,
        original_image_id=db_original_image.id,
        created_by_id=user_id
    )
    
    result = crud.create_leaderboard(
        db=db, 
        leaderboard=db_leaderboard,
    )

    db_story=crud.get_story(db, story_id=story_id)
    if db_story is None:
        story=None
    else:
        story=Path(db_story.textfile_path).read_text()

    background_tasks.add_task(
        generateDescription,
        db=db,
        leaderboard_id=result.id, 
        image=str(image_path), 
        story=story, 
        model_name="gpt-4o-mini"
    )

    return result

@app.get("/leaderboards/{leaderboard_id}", tags=["Leaderboard"], response_model=schemas.LeaderboardOut)
def read_leaderboard(leaderboard_id: int, db: Session = Depends(get_db)):
    db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
    if db_leaderboard is None:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    return db_leaderboard

@app.get("/leaderboards/{leaderboard_id}/rounds/", tags=["Leaderboard", "Round"], response_model=list[schemas.RoundOut])
def get_rounds_by_leaderboard(
    leaderboard_id: int,
    db: Session = Depends(get_db),
):
    return crud.get_rounds(
        db=db,
        leaderboard_id=leaderboard_id,
    )

@app.post("/round/", tags=["Round"], response_model=schemas.Round)
def create_round(
    thisround: schemas.RoundCreate,
    player_id: int,
    db: Session = Depends(get_db),
):
    db_round = crud.create_round(
        db=db,
        leaderboard_id=thisround.leaderboard_id,
        user_id=player_id,
        model_name=thisround.model,
        created_at=thisround.created_at,
    )

    crud.create_message(
        db=db,
        message=schemas.MessageBase(
            content="画像はシステムにインポートされました。ヒントを求めることができます。",
            sender="assistant"
        ),
        chat_id=db_round.chat_history
    )

    return db_round

@app.put("/round/{round_id}", tags=["Round"], response_model=schemas.GenerationCorrectSentence)
def get_user_answer(
    round_id: int,
    generation: schemas.GenerationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    db_generation = crud.create_generation(
        db=db,
        round_id=round_id,
        generation=generation,
    )

    try:
        correct_sentence=sentence.checkSentence(sentence=db_generation.sentence)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    db_round = crud.get_round(db, round_id)

    background_tasks.add_task(
        update_vocab_used_time,
        db=db,
        sentence=db_generation.sentence,
        user_id=db_round.player_id
    )

    return crud.update_generation1(
        db=db,
        generation=schemas.GenerationCorrectSentence(
            id=db_generation.id,
            correct_sentence=correct_sentence
        )
    )

@app.put("/round/{round_id}/interpretation", tags=["Round"], response_model=schemas.GenerationInterpretation)
def get_interpretation(
    round_id: int,
    generation: schemas.GenerationCorrectSentence,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    interpreted_image_url = gen_image.generate_interpretion(
        sentence=generation.correct_sentence
    )
    image_filename = f"i_{round_id}"
    interpreted_image_path = media_dir / "interpreted_images" / f"{image_filename}.jpg"

    try:
        b_interpreted_image = io.BytesIO(requests.get(interpreted_image_url).content)
        interpreted_image = Image.open(b_interpreted_image)
    except Exception:
        raise HTTPException(status_code=400, detail="Please upload a valid image file")
    
    try:
        counter = 0
        while True:
            if not os.path.isfile(interpreted_image_path):
                with open(interpreted_image_path, "wb") as buffer:
                    interpreted_image.save(buffer)
                break
            counter += 1
            interpreted_image_path=media_dir / "interpreted_images" / f"{image_filename}_{counter}.jpg"

    except Exception:
        raise HTTPException(status_code=400, detail="There was an error uploading the file")
    finally:
        interpreted_image.close()
    
    db_interpreted_image = crud.create_interpreted_image(
        db=db,
        image=schemas.ImageBase(
            image_path=str(interpreted_image_path),
        )
    )

    db_generation = crud.update_generation2(
        db=db,
        generation=schemas.GenerationInterpretation(
            id=round_id,
            interpreted_image_id=db_interpreted_image.id,
        )
    )

    generation_complete = schemas.GenerationCompleteCreate(
        id=round_id,
        at=db_generation.created_at
    )

    background_tasks.add_task(
        calculate_score,
        db=db,
        generation=generation_complete,
        is_completed=False
    )

    db_round = crud.get_round(db, round_id)

    new_message="""
回答をシステム入力しました。📝
回答: {}
""".format(generation.correct_sentence)

    crud.create_message(
        db=db,
        message=schemas.MessageBase(
            content=new_message,
            sender="assistant"
        ),
        chat_id=db_round.chat_history
    )

    return db_generation

@app.put("/round/{round_id}/complete", tags=["Round"], response_model=schemas.GenerationComplete)
def complete_generation(
    generation: schemas.GenerationCompleteCreate,
    db: Session = Depends(get_db),
):
    db_generation = crud.get_generation(db, generation_id=generation.id)
    db_round = crud.get_round(db, db_generation.round_id)
    db_chat = crud.get_chat(db=db,chat_id=db_round.chat_history)
    cb=openai_chatbot.Hint_Chatbot()

    factors, scores_dict = calculate_score(
        db=db,
        generation=generation,
        is_completed=True
    )
    if 'grammar_error' in factors:
        grammar_errors=str(factors['grammar_error'])
        spelling_errors=str(factors['spelling_error'])
    elif factors['n_grammar_errors'] > 0:
        errors = score.grammar_spelling_errors(db_generation.sentence)
        grammar_errors=str(errors['grammar_error'])
        spelling_errors=str(errors['spelling_error'])
    else:
        grammar_errors='None'
        spelling_errors='None'

    evaluation = cb.get_result(
        sentence=db_generation.sentence,
        scoring=scores_dict,
        rank=db_generation.rank,
        original_image=db_round.leaderboard.original_image.image_path,
        chat_history=db_chat.messages,
        grammar_errors=grammar_errors,
        spelling_errors=spelling_errors
    )

    if evaluation:
        evaluation_message = """あなたの回答：{user_sentence}
        Grammar Score: {grammar_score} (out of 5)
        Spelling Score: {spelling_score} (out of 5)
        Vividness Score: {vividness_score} (out of 5)
        Convention Score: {convention} (out of 5)
        Structure Score: {structure_score} (out of 3)
        Content Comprehensive Score: {content_score} (out of 100)
        Total Score: {total_score} (out of 2300)
        Rank: {rank}
        
        文法について
        {grammar_feedback}
        スペルについて
        {spelling_feedback}
        スタオルについて
        {style_feedback}
        内容について
        {content_feedback}

        整体的なコメント
        {overall_feedback}
        """.format(
            user_sentence=db_round.correct_sentence,
            grammar_score=scores_dict['grammar_score'],
            spelling_score=scores_dict['spelling_score'],
            vividness_score=scores_dict['vividness_score'],
            convention=scores_dict['convention'],
            structure_score=scores_dict['structure_score'],
            content_score=scores_dict['content_score'],
            total_score=scores_dict['total_score'],
            rank=db_generation.rank,
            grammar_feedback=evaluation.grammar_evaluation,
            spelling_feedback=evaluation.spelling_evaluation,
            style_feedback=evaluation.style_evaluation,
            content_feedback=evaluation.content_evaluation,
            overall_feedback=evaluation.overall_evaluation
        )

        crud.create_message(
            db=db,
            message=schemas.MessageBase(
                content=evaluation_message,
                sender="assistant" 
            ),
            chat_id=db_round.chat_history
        )

    return crud.get_generation(db, generation_id=generation.id)

@app.post("/round/{round_id}/end",tags=["Round"], response_model=schemas.RoundOut)
def end_round(
    round_id: int,
    db: Session = Depends(get_db),
):
    db_round = crud.get_round(db, round_id)

    now_tim = datetime.datetime.now(tz=timezone.utc)
    db_generation_aware = db_round.created_at.replace(tzinfo=timezone.utc)
    duration = (now_tim - db_generation_aware).seconds


    db_round = crud.complete_round(db, round_id, schemas.RoundComplete(
        id=round_id,
        last_generation_id=db_round.last_generation_id,
        duration=duration,
        is_completed=True
    ))

    return db_round

@app.get("/personal_dictionaries/", tags=["Personal Dictionary"], response_model=list[schemas.PersonalDictionary])
def read_personal_dictionaries(player_id: int, db: Session = Depends(get_db)):
    personal_dictionaries = crud.get_personal_dictionaries(db, player_id=player_id)
    return personal_dictionaries

@app.post("/personal_dictionary/", tags=["Personal Dictionary"], response_model=schemas.PersonalDictionary)
def create_personal_dictionary(
    personal_dictionary: schemas.PersonalDictionaryCreate,
    db: Session = Depends(get_db),
):
    word_lemma = dictionary.get_pos_lemma(
        word=personal_dictionary.vocabulary,
        relevant_sentence=personal_dictionary.relevant_sentence
    )
    
    vocab = crud.get_vocabulary(
        db=db,
        vocabulary=word_lemma['lemma'],
        part_of_speech=word_lemma['pos']
    )

    if not vocab:
        meanings=dictionary.get_meaning(
            lemma=word_lemma['lemma'],
            pos=word_lemma['pos']
        )
        if isinstance(meanings, list):
            meaning = '; '.join(meanings)
        else:
            meaning = meanings

        vocab = crud.create_vocabulary(
            db=db,
            vocabulary=schemas.VocabularyBase(
                word=word_lemma['lemma'],
                pos=word_lemma['pos'],
                meaning=meaning
            )
        )

    return crud.create_personal_dictionary(
                db=db,
                user_id=personal_dictionary.user_id,
                vocabulary_id=vocab.id,
                round_id=personal_dictionary.save_at_round_id,
                created_at=personal_dictionary.created_at,
    )

@app.put("/personal_dictionary/{personal_dictionary_id}", tags=["Personal Dictionary"], response_model=schemas.PersonalDictionary)
def update_personal_dictionary(
    personal_dictionary: schemas.PersonalDictionaryUpdate,
    personal_dictionary_id: int,
    db: Session = Depends(get_db),
):
    return crud.update_personal_dictionary(
        db=db,
        dictionary=personal_dictionary,
    )

@app.delete("/personal_dictionary/{personal_dictionary_id}", tags=["Personal Dictionary"], response_model=schemas.PersonalDictionary)
def delete_personal_dictionary(
    personal_dictionary_id: int,
    user_id: int,
    db: Session = Depends(get_db),
):
    return crud.delete_personal_dictionary(
        db=db,
        player_id=user_id,
        vocabulary_id=personal_dictionary_id,
    )

@app.get("/chat/{chat_id}", tags=["Chat"], response_model=schemas.Chat)
def read_chat(chat_id: int, db: Session = Depends(get_db)):
    chat = crud.get_chat(db, chat_id=chat_id)
    return chat

@app.put("/round/{round_id}/chat", tags=["Chat"], response_model=schemas.Chat)
def update_chat(
    round_id: int,
    message: schemas.MessageReceive,
    db: Session = Depends(get_db),
):
    db_round = crud.get_round(db, round_id)
    if db_round is None:
        raise HTTPException(status_code=404, detail="Round not found")
    
    if db_round.is_completed:
        raise HTTPException(status_code=400, detail="The round is already ended.")
    
    db_chat = crud.get_chat(db=db, chat_id=db_round.chat_history)
    if db_chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    db_new=crud.create_message(
        db=db,
        message=schemas.MessageBase(
            content=message.content,
            sender="user"
        ),
        chat_id=db_chat.id
    )

    # get hint from AI
    cb = openai_chatbot.Hint_Chatbot()

    model_response = cb.nextResponse(
        ask_for_hint=message.content,
        chat_history=db_chat.messages,
        original_image=db_round.leaderboard.original_image.image_path,
    )
    if model_response:
        result = crud.create_message(
            db=db,
            message=schemas.MessageBase(
                content=model_response.hints,
                sender="assistant"
            ),
            chat_id=db_chat.id
        )

        return result
    else:
        raise HTTPException(status_code=400, detail="Error in chatbot response")

@app.get("/original_image/{leaderboard_id}", tags=["Image"])
async def get_original_image(leaderboard_id: int, db: Session = Depends(get_db)):
    db_leaderboard = crud.get_leaderboard(
        db=db,
        leaderboard_id=leaderboard_id
    )
    image_name = db_leaderboard.original_image.image_path.split('/')[-1]
    # Construct the image path
    image_path = os.path.join('/static','original_images', image_name)
    
    # Check if the file exists
    if os.path.isfile(image_path):
        # Return the image as a file response
        return responses.FileResponse(image_path, media_type="image/jpeg")
    else:
        raise HTTPException(status_code=404, detail="Image not found")
    
@app.get("/interpreted_image/{round_id}", tags=["Image"])
async def get_interpreted_image(round_id: int, db: Session = Depends(get_db)):
    db_round = crud.get_round(
        db=db,
        round_id=round_id
    )
    image_name = db_round.interpreted_image.image_path.split('/')[-1]
    # Construct the image path
    image_path = os.path.join('/static','interpreted_images', image_name)
    
    # Check if the file exists
    if os.path.isfile(image_path):
        # Return the image as a file response
        return responses.FileResponse(image_path, media_type="image/jpeg")
    else:
        raise HTTPException(status_code=404, detail="Image not found")
    