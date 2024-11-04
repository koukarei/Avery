from fastapi import Depends, FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks, responses
from sqlalchemy.orm import Session
import shutil, time, os, datetime, io, requests
from pathlib import Path
from PIL import Image

from . import crud, models, schemas
from .database import SessionLocal, engine

from .dependencies import sentence, gen_image, score, dictionary, chatbot

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
    thisround: schemas.RoundCompleteCreate,
    is_completed: bool=False
):

    db_round = crud.get_round(db, thisround.id)
    if db_round is None:
        raise HTTPException(status_code=404, detail="Round not found")
    
    if db_round.duration==0 or db_round.total_score==0:

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


        effective_score = score.cosine_similarity_to_ai(
            ai_play=[ai.content for ai in ai_play],
            corrected_sentence=db_round.correct_sentence,
        )

        grammar_score = score.semantic_similarity(
            sentence=db_round.sentence,
            corrected_sentence=db_round.correct_sentence,
        )

        vocab_score = score.vocab_difficulty(
            corrected_sentence=db_round.correct_sentence,
        )

        total_score = (effective_score+grammar_score+vocab_score)/3

        if is_completed:
            thisround_aware = thisround.at.replace(tzinfo=timezone.utc)
            db_round_aware = db_round.created_at.replace(tzinfo=timezone.utc)
            duration = (thisround_aware - db_round_aware).seconds
        else: 
            duration = 0

        round_com = schemas.RoundComplete(
            id=db_round.id,
            grammar_score=int(grammar_score*100),
            vocabulary_score=int(vocab_score*100),
            effectiveness_score=int(effective_score*100),
            total_score=int(total_score*100),
            rank=score.rank(total_score),
            duration=duration,
            is_completed=is_completed
        )
    else:

        thisround_aware = thisround.at.replace(tzinfo=timezone.utc)
        db_round_aware = db_round.created_at.replace(tzinfo=timezone.utc)
        duration = (thisround_aware - db_round_aware).seconds

        round_com = schemas.RoundComplete(
            id=db_round.id,
            grammar_score=db_round.grammar_score,
            vocabulary_score=db_round.vocabulary_score,
            effectiveness_score=db_round.effectiveness_score,
            total_score=db_round.total_score,
            rank=db_round.rank,
            duration=duration,
            is_completed=is_completed
        )


    return crud.update_round4(
        db=db,
        round_id=thisround.id,
        round=round_com,
    )

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
            content="The image is imported to my system. You can ask me for a hint.",
            sender="model"
        ),
        chat_id=db_round.chat_history
    )

    return db_round


@app.put("/round/{round_id}", tags=["Round"], response_model=schemas.RoundCorrectSentence)
def get_user_answer(
    round_id: int,
    thisround: schemas.RoundSentence,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    db_round = crud.update_round1(
        db=db,
        round_id=round_id,
        round=thisround,
    )

    try:
        correct_sentence=sentence.checkSentence(sentence=db_round.sentence)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    background_tasks.add_task(
        update_vocab_used_time,
        db=db,
        sentence=db_round.sentence,
        user_id=db_round.player_id
    )

    return crud.update_round2(
        db=db,
        round_id=round_id,
        round=schemas.RoundCorrectSentence(
            id=db_round.id,
            correct_sentence=correct_sentence
        ),
    )

@app.put("/round/{round_id}/interpretation", tags=["Round"], response_model=schemas.RoundInterpretation)
def get_interpretation(
    round_id: int,
    thisround: schemas.RoundCorrectSentence,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    interpreted_image_url = gen_image.generate_interpretion(
        sentence=thisround.correct_sentence,
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

    db_round = crud.update_round3(
        db=db,
        round_id=round_id,
        round=schemas.RoundInterpretation(
            id=round_id,
            interpreted_image_id=db_interpreted_image.id,
        ),
    )

    thisround_complete = schemas.RoundCompleteCreate(
        id=round_id,
        at=db_round.created_at
    )

    background_tasks.add_task(
        calculate_score,
        db=db,
        thisround=thisround_complete,
        is_completed=False
    )

    new_message="""
We input the sentence into Skyler's system. 📝
Sentence: {}
""".format(thisround.correct_sentence)

    crud.create_message(
        db=db,
        message=schemas.MessageBase(
            content=new_message,
            sender="model"
        ),
        chat_id=db_round.chat_history
    )

    return db_round

@app.put("/round/{round_id}/complete", tags=["Round"], response_model=schemas.RoundComplete)
def complete_round(
    thisround: schemas.RoundCompleteCreate,
    db: Session = Depends(get_db),
):
    db_round = crud.get_round(db, thisround.id)
    db_chat = crud.get_chat(db=db,chat_id=db_round.chat_history)
    cb=chatbot.Hint_Chatbot()
    evaluation = cb.get_result(
        generated_image=db_round.interpreted_image.image_path,
        sentence=db_round.correct_sentence,
        scoring="Effectiveness Score: %d Vocabulary Score: %d".format(db_round.effectiveness_score,db_round.vocabulary_score),
        original_image=db_round.leaderboard.original_image.image_path,
        chat_history=db_chat.messages,
    )

    crud.create_message(
        db=db,
        message=schemas.MessageBase(
            content=evaluation,
            sender="model"
        ),
        chat_id=db_round.chat_history
    )

    return calculate_score(
        db=db,
        thisround=thisround,
        is_completed=True
    )

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
    cb = chatbot.Hint_Chatbot()

    model_response = cb.nextResponse(
        ask_for_hint=message.content,
        chat_history=db_new['chat'].messages,
        original_image=db_round.leaderboard.original_image.image_path,
    )

    result = crud.create_message(
        db=db,
        message=schemas.MessageBase(
            content=model_response,
            sender="model"
        ),
        chat_id=db_chat.id
    )

    return result

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
    