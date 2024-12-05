import logging.config
from fastapi import Depends, FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks, responses, Security, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import time, os, datetime, io, requests
from pathlib import Path
from PIL import Image

from . import crud, models, schemas
from .database import SessionLocal, engine

from .dependencies import sentence, gen_image, score, dictionary, openai_chatbot
from authentication import *
import tracemalloc
tracemalloc.start()

from typing import Union, List, Annotated, Optional
from datetime import timezone, timedelta
import torch, stanza
from contextlib import asynccontextmanager
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

class memory_tracker:
    def __init__(self, message=None):
        self.filehandler = logging.FileHandler("logs/memory_tracker.log", mode="a", encoding=None, delay=False)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.WARNING)
        self.logger.addHandler(self.filehandler)
        self.filehandler.setFormatter(formatter)
        self.logger.warning(f"{message} - Memory tracker started")
        self.snapshot1 = tracemalloc.take_snapshot()

    def get_top_stats(self, message=None):
        snapshot2 = tracemalloc.take_snapshot()
        top_stats = snapshot2.compare_to(self.snapshot1, 'lineno')
        if message:
            self.logger.warning(message)
        self.logger.warning("[ Top 10 ]")
        for stat in top_stats[:10]:
            self.logger.warning(stat)
        return top_stats

log_filename = "logs/backend.log"

os.makedirs(os.path.dirname(log_filename), exist_ok=True)
file_handler = logging.FileHandler(log_filename, mode="a", encoding=None, delay=False)
file_handler.setFormatter(formatter)

logger1 = logging.getLogger(
    "info_logger"
)
logger1.setLevel(logging.INFO)
logger1.addHandler(file_handler)

from .background_tasks import *

models.Base.metadata.create_all(bind=engine)
nlp_models = {}

def model_load():
    logger1.info("Loading models: stanza, GPT-2")
    en_nlp = stanza.Pipeline('en', processors='tokenize,pos,constituency', package='default_accurate')
    from transformers import GPT2Tokenizer, GPT2LMHeadModel
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    perplexity_model = GPT2LMHeadModel.from_pretrained("gpt2")
    perplexity_model.eval()
    if torch.cuda.is_available():
        perplexity_model.to('cuda')
    return en_nlp, tokenizer, perplexity_model

app = FastAPI(
    debug=True,
    title="AVERY",
    lifespan=lifespan,
)

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

def create_admin_acc(db: Session):
    username = os.getenv("ADMIN_USERNAME")
    user=crud.get_user_by_username(db, username=username)
    if user is None:
        admin = schemas.UserCreate(
            username=os.getenv("ADMIN_USERNAME"),
            email=os.getenv("ADMIN_EMAIL"),
            password=os.getenv("ADMIN_PASSWORD"),
            display_name="Admin",
            is_admin=True
        )
        crud.create_user(
            db=db,
            user=admin
        )
    return


@asynccontextmanager
async def lifespan(app: FastAPI):
    await logger1.info("Starting up")
    try:
        # Download the English model for stanza
        stanza.download('en')
        nlp_models['en_nlp'], nlp_models['tokenizer'], nlp_models['perplexity_model'] = await model_load()
        logger1.info("Models loaded successfully")
        create_admin_acc(SessionLocal())
        yield
    except Exception as e:
        print(f"Error in lifespan startup: {e}")
        raise
    finally:
        await logger1.info("Shutting down")
        await nlp_models.clear()

@app.get("/")
def hello_world():
    logger1.info("Hello World")
    return {"message": "Hello World"}

async def get_current_user(db: Annotated[Session, Depends(get_db)],token: Annotated[schemas.TokenData, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = schemas.TokenData(username=username)
        except JWTError:
            raise credentials_exception
        except jwt.ExpiredSignatureError:
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
        user = crud.get_user_by_username(db, username=token_data.username)
        if user is None:
            raise credentials_exception
        return user
    else:
        raise credentials_exception

async def get_admin(
        db: Annotated[Session, Depends(get_db)],
        token: Annotated[schemas.TokenData, Depends(oauth2_scheme)]
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="You are not an admin",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token:
        user = get_current_user(db, token)
        if user.is_admin:
            return user
        else:
            raise credentials_exception
    else:
        raise credentials_exception

@app.post("/token",response_model=schemas.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(user.username)
    
    return schemas.Token(access_token=access_token,refresh_token=refresh_token, token_type="bearer")

@app.post("/refresh_token")
async def refresh_token(current_user: schemas.User = Security(get_current_user, scopes=["refresh_token"])):
    if current_user:
            access_token = create_access_token(
                data={"sub": current_user.username}
            )
            return {"access_token": access_token}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer",
                    "Current User":current_user.username},
        )

@app.post("/content_score/")
def content_score_test_endpoint(
    image: Annotated[UploadFile, File()],
    sentence: Annotated[str, Form()],
):
    temp_image_path = media_dir / "temp.jpg"
    try:
        image.file.seek(0)
        image_content = Image.open(image.file)
    except Exception:
        raise HTTPException(status_code=400, detail="Please upload a valid image file")
    
    try:
        image_content.save(temp_image_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error uploading file: {str(e)}")
    finally:
        image.file.close()
    output = score.calculate_content_score(
        image_path=temp_image_path,
        sentence=sentence
    )
    if os.path.isfile(temp_image_path):
        os.remove(temp_image_path)
    return output

@app.post("/users/", tags=["User"], response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    user.is_admin=False
    return crud.create_user(db=db, user=user)

@app.delete("/users/{user_id}", tags=["User"], response_model=schemas.UserBase)
def delete_user(admin: Annotated[schemas.User, Depends(get_admin)], user_id: int, db: Session = Depends(get_db), ):
    if not admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return crud.delete_user(db=db, user_id=user_id)

@app.get("/users/", tags=["User"], response_model=list[schemas.User])
def read_users(admin: Annotated[schemas.User, Depends(get_admin)],skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@app.get("/users/{user_id}", tags=["User"], response_model=schemas.User)
def read_user(admin: Annotated[schemas.User, Depends(get_admin)],user_id: int, db: Session = Depends(get_db)):
    if not admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/scenes/", tags=["Scene"], response_model=list[schemas.Scene])
def read_scenes(admin: Annotated[schemas.User, Depends(get_admin)],skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    scenes = crud.get_scenes(db, skip=skip, limit=limit)
    return scenes

@app.post("/scene/", tags=["Scene"], response_model=schemas.Scene)
def create_scene(admin: Annotated[schemas.User, Depends(get_admin)],scene: schemas.SceneBase, db: Session = Depends(get_db)):
    if not admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    return crud.create_scene(db=db, scene=scene)
    
@app.get("/stories/", tags=["Story"], response_model=list[schemas.StoryOut])
def read_stories(admin: Annotated[schemas.User, Depends(get_admin)],skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    stories = crud.get_stories(db, skip=skip, limit=limit)
    return stories
        

@app.post("/story/", tags=["Story"], response_model=schemas.StoryOut)
def create_story(
    admin: Annotated[schemas.User, Depends(get_admin)],
    story_content_file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    scene_id: Annotated[int, Form()],
    db: Session = Depends(get_db),
):
    if not admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    os.makedirs(media_dir / "stories", exist_ok=True)
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
        logger1.error(f"Error uploading file: {Exception}")
        raise HTTPException(status_code=400, detail="Error uploading file")
    finally:
        story_content_file.file.close()

    storyCreate = schemas.StoryCreate(
        title=title,
        scene_id=scene_id,
        textfile_path=str(textfile_path)
    )

    return crud.create_story(db=db, story=storyCreate)


@app.get("/leaderboards/", tags=["Leaderboard"], response_model=list[schemas.LeaderboardOut])
def read_leaderboards(current_user: Annotated[schemas.User, Depends(get_current_user)],skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if current_user:
        raise HTTPException(status_code=401, detail="Login to view leaderboards")
    leaderboards = crud.get_leaderboards(db, skip=skip, limit=limit)
    return leaderboards

@app.post("/leaderboards/", tags=["Leaderboard"], response_model=schemas.LeaderboardOut)
def create_leaderboard(
    admin: Annotated[schemas.User, Depends(get_admin)],
    leaderboard: schemas.LeaderboardCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    story_id = leaderboard.story_id
    if story_id==0:
        story_id=None
    
    result = crud.create_leaderboard(
        db=db, 
        leaderboard=leaderboard,
    )

    db_story=crud.get_story(db, story_id=story_id)
    if db_story is None:
        story=None
    else:
        story=Path(db_story.textfile_path).read_text()

    db_original_image = crud.get_original_image(db, image_id=leaderboard.original_image_id)
    image_path = db_original_image.image_path

    background_tasks.add_task(
        generateDescription,
        db=db,
        leaderboard_id=result.id, 
        image=str(image_path), 
        story=story, 
        model_name="gpt-4o-mini"
    )

    return result

@app.post("/leaderboards/image", tags=["Leaderboard"], response_model=schemas.IdOnly)
def create_leaderboard_image(
    admin: Annotated[schemas.User, Depends(get_admin)],
    original_image: Annotated[UploadFile, File()],
    db: Session = Depends(get_db),
):
    if not admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    
    timestamp = str(int(time.time()))
    shortenfilename=".".join(original_image.filename.split(".")[:-1])[:20]
    fileattr = original_image.filename.split(".")[-1:][0]
    filename = f"o_{timestamp}_{shortenfilename}.{fileattr}"
    image_path = media_dir / "original_images" / filename

    os.makedirs(media_dir / "original_images", exist_ok=True)

    try:
        original_image.file.seek(0)
        image_content = Image.open(original_image.file)
    except Exception:
        raise HTTPException(status_code=400, detail="Please upload a valid image file")

    counter = 0
    while os.path.isfile(image_path):
        counter += 1
        image_path=media_dir / "original_images" / f"o_{timestamp}_{shortenfilename}_{counter}.{fileattr}"
    
    try:
        image_content.save(image_path)
    except Exception as e:
        logger1.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error uploading file: {str(e)}")
    finally:
        original_image.file.close()
        
    db_original_image = crud.create_original_image(
        db=db,
        image=schemas.ImageBase(
            image_path=str(image_path),
        )
    )

    return db_original_image

@app.get("/leaderboards/{leaderboard_id}", tags=["Leaderboard"], response_model=schemas.LeaderboardOut)
def read_leaderboard(current_user: Annotated[schemas.User, Depends(get_current_user)],leaderboard_id: int, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view leaderboards")
    db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
    if db_leaderboard is None:
        logger1.error(f"Leaderboard not found: {leaderboard_id}")
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    return db_leaderboard

@app.get("/leaderboards/{leaderboard_id}/rounds/", tags=["Leaderboard", "Round"], response_model=list[schemas.RoundOut])
def get_rounds_by_leaderboard(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard_id: int,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view")
    return crud.get_rounds(
        db=db,
        leaderboard_id=leaderboard_id,
    )

@app.get("/unfinished_rounds/", tags=["Round"], response_model=list[schemas.RoundOut])
def get_unfinished_rounds(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if not current_user:
        return []
    player_id = current_user.id
    return crud.get_rounds(
        db=db,
        is_completed=False,
        player_id=player_id
    )

@app.post("/round/", tags=["Round"], response_model=schemas.Round)
def create_round(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    thisround: schemas.RoundCreate,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to create a round")
    player_id = current_user.id
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
            sender="assistant",
            created_at=datetime.datetime.now(tz=timezone.utc)
        ),
        chat_id=db_round.chat_history
    )

    return db_round

@app.put("/round/{round_id}", tags=["Round"], response_model=schemas.GenerationCorrectSentence)
def get_user_answer(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    round_id: int,
    generation: schemas.GenerationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to answer")
    db_round = crud.get_round(db, round_id)
    if current_user.id != db_round.player_id:
        raise HTTPException(status_code=401, detail="You are not authorized to answer")
    db_generation = crud.create_generation(
        db=db,
        round_id=round_id,
        generation=generation,
    )
 
    try:
        status, correct_sentence=sentence.checkSentence(sentence=db_generation.sentence)

    except Exception as e:
        logger1.error(f"Error in get_user_answer: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    db_round = crud.get_round(db, round_id)

    background_tasks.add_task(
        update_vocab_used_time,
        db=db,
        sentence=db_generation.sentence,
        user_id=db_round.player_id
    )

    if status == 0:
        return crud.update_generation1(
            db=db,
            generation=schemas.GenerationCorrectSentence(
                id=db_generation.id,
                correct_sentence=correct_sentence
            )
        )
    elif status == 1:
        crud.create_message(
            db=db,
            message=schemas.MessageBase(
                content="ブー！英語で答えてください。",
                sender="assistant",
                created_at=datetime.datetime.now(tz=timezone.utc)
            ),
        )
    elif status == 2:
        crud.create_message(
            db=db,
            message=schemas.MessageBase(
                content="ブー！不適切な言葉が含まれています。",
                sender="assistant",
                created_at=datetime.datetime.now(tz=timezone.utc)
            ),
            chat_id=db_round.chat_history
        )
    return None

@app.put("/round/{round_id}/interpretation", tags=["Round"], response_model=schemas.GenerationInterpretation)
def get_interpretation(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    round_id: int,
    generation: schemas.GenerationCorrectSentence,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to get interpretation")
    db_round = crud.get_round(db, round_id)
    if current_user.id != db_round.player_id:
        raise HTTPException(status_code=401, detail="You are not authorized to get interpretation")
    
    tracker_interpretation = memory_tracker(message=f"Round id: {round_id}, Generation id: {generation.id} - Get interpretation")
    try:

        # Image generation
        interpreted_image_url = gen_image.generate_interpretion(
            sentence=generation.correct_sentence
        )
        image_filename = f"i_{round_id}_{generation.id}"
        interpreted_image_path = media_dir / "interpreted_images" / f"{image_filename}.jpg"

        # Download and save image
        try:
            b_interpreted_image = io.BytesIO(requests.get(interpreted_image_url).content)
            interpreted_image = Image.open(b_interpreted_image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
        
        try:
            counter = 0
            while True:
                if not os.path.isfile(interpreted_image_path):
                    with open(interpreted_image_path, "wb") as buffer:
                        interpreted_image.save(buffer)
                    break
                counter += 1
                interpreted_image_path = media_dir / "interpreted_images" / f"{image_filename}_{counter}.jpg"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error uploading file: {str(e)}")
        finally:
            interpreted_image.close()
        
        # Database operations
        db_interpreted_image = crud.create_interpreted_image(
            db=db,
            image=schemas.ImageBase(
                image_path=str(interpreted_image_path),
            )
        )

        db_generation = crud.update_generation2(
            db=db,
            generation=schemas.GenerationInterpretation(
                id=generation.id,
                interpreted_image_id=db_interpreted_image.id,
            )
        )

        generation_complete = schemas.GenerationCompleteCreate(
            id=generation.id,
            at=db_generation.created_at
        )

        # Safe background task addition with error handling
        try:

            if 'en_nlp' not in nlp_models or 'perplexity_model' not in nlp_models or 'tokenizer' not in nlp_models:
                nlp_models['en_nlp'], nlp_models['tokenizer'], nlp_models['perplexity_model'] = model_load()

            # Update scores in background
            background_tasks.add_task(
                update_perplexity,
                db=db,
                en_nlp=nlp_models['en_nlp'],
                perplexity_model=nlp_models['perplexity_model'],
                tokenizer=nlp_models['tokenizer'],
                generation=generation_complete
            )
            
            background_tasks.add_task(
                update_content_score,
                db=db,
                generation=generation_complete
            )

            background_tasks.add_task(
                update_frequency_word,
                db=db,
                en_nlp=nlp_models['en_nlp'],
                generation=generation_complete
            )

            background_tasks.add_task(
                update_n_words,
                db=db,
                en_nlp=nlp_models['en_nlp'],
                generation=generation_complete
            )
        except Exception as e:
            # Log the background task error without raising
            logger1.error(f"Error in background task addition: {str(e)}")

        # Get round and create message
        db_round = crud.get_round(db, round_id)

        new_message = """回答をシステム入力しました。📝
回答: {}""".format(generation.correct_sentence)

        crud.create_message(
            db=db,
            message=schemas.MessageBase(
                content=new_message,
                sender="assistant",
                created_at=datetime.datetime.now(tz=timezone.utc)
            ),
            chat_id=db_round.chat_history
        )

        tracker_interpretation.get_top_stats(message=f"Round id: {round_id}, Generation id: {generation.id}")
        del tracker_interpretation
        return db_generation

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch and log any unexpected errors
        logger1.error(f"Unexpected error in get_interpretation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/round/{round_id}/complete", tags=["Round"], response_model=schemas.GenerationComplete)
def complete_generation(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    generation: schemas.GenerationCompleteCreate,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to complete generation")
    
    db_generation = crud.get_generation(db, generation_id=generation.id)
    if db_generation is None:
        raise HTTPException(status_code=404, detail="Generation not found")
    db_round = crud.get_round(db, db_generation.round_id)
    if db_round is None:
        raise HTTPException(status_code=404, detail="Round not found")
    
    if current_user.id != db_round.player_id:
        raise HTTPException(status_code=401, detail="You are not authorized to complete generation")
    
    tracker_complete_generation = memory_tracker(message=f"Generation id: {generation.id} - Complete a generation")

    db_chat = crud.get_chat(db=db,chat_id=db_round.chat_history)
    cb=openai_chatbot.Hint_Chatbot()

    if 'en_nlp' not in nlp_models or 'perplexity_model' not in nlp_models or 'tokenizer' not in nlp_models:
        nlp_models['en_nlp'], nlp_models['tokenizer'], nlp_models['perplexity_model'] = model_load()

    factors, scores_dict = calculate_score(
        db=db,
        en_nlp=nlp_models['en_nlp'],
        perplexity_model=nlp_models['perplexity_model'],
        tokenizer=nlp_models['tokenizer'],
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
        score_message = """あなたの回答：{user_sentence}
        Grammar Score: {grammar_score} (out of 5)
        Spelling Score: {spelling_score} (out of 5)
        Vividness Score: {vividness_score} (out of 5)
        Convention Score: {convention} (out of 5)
        Structure Score: {structure_score} (out of 3)
        Content Comprehensive Score: {content_score} (out of 100)
        Total Score: {total_score} (out of 2300)
        Rank: {rank}
        """.format(
            user_sentence=db_generation.sentence,
            grammar_score=scores_dict['grammar_score'],
            spelling_score=scores_dict['spelling_score'],
            vividness_score=scores_dict['vividness_score'],
            convention=scores_dict['convention'],
            structure_score=scores_dict['structure_score'],
            content_score=scores_dict['content_score'],
            total_score=scores_dict['total_score'],
            rank=db_generation.rank,
        )

        evaluation_message = """文法について
        {grammar_feedback}
        スペルについて
        {spelling_feedback}
        スタオルについて
        {style_feedback}
        内容について
        {content_feedback}
        """.format(
            grammar_feedback=evaluation.grammar_evaluation,
            spelling_feedback=evaluation.spelling_evaluation,
            style_feedback=evaluation.style_evaluation,
            content_feedback=evaluation.content_evaluation
        )

        overall_evaluation_message = """整体的なコメント
        {overall_feedback}
        """.format(
            overall_feedback=evaluation.overall_evaluation
        )

        crud.create_message(
            db=db,
            message=schemas.MessageBase(
                content=score_message,
                sender="assistant",
                created_at=datetime.datetime.now(tz=timezone.utc)
            ),
            chat_id=db_round.chat_history
        )

        crud.create_message(
            db=db,
            message=schemas.MessageBase(
                content=evaluation_message,
                sender="assistant",
                created_at=datetime.datetime.now(tz=timezone.utc)
            ),
            chat_id=db_round.chat_history
        )

        crud.create_message(
            db=db,
            message=schemas.MessageBase(
                content=overall_evaluation_message,
                sender="assistant",
                created_at=datetime.datetime.now(tz=timezone.utc)
            ),
            chat_id=db_round.chat_history
        )

    tracker_complete_generation.get_top_stats(
        message=f"Generation id: {generation.id} - Complete a generation"
    )
    del tracker_complete_generation
    return crud.get_generation(db, generation_id=generation.id)

@app.post("/round/{round_id}/end",tags=["Round"], response_model=schemas.RoundOut)
def end_round(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    round_id: int,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to end round")
    
    db_round = crud.get_round(db, round_id)
    if db_round is None:
        raise HTTPException(status_code=404, detail="Round not found")
    
    if current_user.id != db_round.player_id:
        raise HTTPException(status_code=401, detail="You are not authorized to end round")

    now_tim = datetime.datetime.now(tz=timezone.utc)
    db_generation_aware = db_round.created_at.replace(tzinfo=timezone.utc)
    duration = (now_tim - db_generation_aware).seconds

    db_round = crud.complete_round(db, round_id, schemas.RoundComplete(
        id=round_id,
        last_generation_id=db_round.last_generation_id,
        duration=duration,
        is_completed=True
    ))

    if db_round is None:
        raise HTTPException(status_code=404, detail="Round not found")
    return db_round

@app.get("/personal_dictionaries/", tags=["Personal Dictionary"], response_model=list[schemas.PersonalDictionary])
def read_personal_dictionaries(current_user: Annotated[schemas.User, Depends(get_current_user)], db: Session = Depends(get_db)):
    if not current_user:
        return []
    player_id = current_user.id
    personal_dictionaries = crud.get_personal_dictionaries(db, player_id=player_id)
    return personal_dictionaries

@app.post("/personal_dictionary/", tags=["Personal Dictionary"], response_model=schemas.PersonalDictionary)
def create_personal_dictionary(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    personal_dictionary: schemas.PersonalDictionaryCreate,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to create personal dictionary")

    personal_dictionary.user_id = current_user.id

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
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    personal_dictionary: schemas.PersonalDictionaryUpdate,
    personal_dictionary_id: int,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to update personal dictionary")
    personal_dictionary.user_id = current_user.id
    return crud.update_personal_dictionary(
        db=db,
        dictionary=personal_dictionary,
    )

@app.delete("/personal_dictionary/{personal_dictionary_id}", tags=["Personal Dictionary"], response_model=schemas.PersonalDictionary)
def delete_personal_dictionary(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    personal_dictionary_id: int,
    db: Session = Depends(get_db),
):
    return crud.delete_personal_dictionary(
        db=db,
        player_id=current_user.id,
        vocabulary_id=personal_dictionary_id,
    )

@app.get("/chat/{round_id}", tags=["Chat"], response_model=schemas.Chat)
def read_chat(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    round_id: int, db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view chat")
    db_round = crud.get_round(db, round_id)
    if db_round is None:
        raise HTTPException(status_code=404, detail="Round not found")
    if current_user.id != db_round.player_id and not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not authorized to view chat")
    chat_id = db_round.chat_history
    chat = crud.get_chat(db, chat_id=chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    return chat

@app.put("/round/{round_id}/chat", tags=["Chat"], response_model=schemas.Chat)
def update_chat(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    round_id: int,
    message: schemas.MessageReceive,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to send message")
    
    db_round = crud.get_round(db, round_id)
    if db_round is None:
        raise HTTPException(status_code=404, detail="Round not found")
    
    if current_user.id != db_round.player_id:
        raise HTTPException(status_code=401, detail="You are not authorized to send message")
    
    if db_round.is_completed:
        raise HTTPException(status_code=400, detail="The round is already ended.")
    
    db_chat = crud.get_chat(db=db, chat_id=db_round.chat_history)
    if db_chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    db_new=crud.create_message(
        db=db,
        message=schemas.MessageBase(
            content=message.content,
            sender="user",
            created_at=datetime.datetime.now(tz=timezone.utc)
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
                content=model_response,
                sender="assistant",
                created_at=datetime.datetime.now(tz=timezone.utc)
            ),
            chat_id=db_chat.id
        )

        return result['chat']
    else:
        raise HTTPException(status_code=400, detail="Error in chatbot response")

@app.get("/original_image/{leaderboard_id}", tags=["Image"])
async def get_original_image(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard_id: int, 
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view images")
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
    
@app.get("/interpreted_image/{generation_id}", tags=["Image"])
async def get_interpreted_image(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    generation_id: int, 
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view images")
    
    db_generation = crud.get_generation(
        db=db,
        generation_id=generation_id
    )

    db_round = crud.get_round(
        db=db,
        round_id=db_generation.round_id
    )

    if current_user.id != db_round.player_id and not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not authorized to view images")

    image_name = db_generation.interpreted_image.image_path.split('/')[-1]
    # Construct the image path
    image_path = os.path.join('/static','interpreted_images', image_name)
    
    # Check if the file exists
    if os.path.isfile(image_path):
        # Return the image as a file response
        return responses.FileResponse(image_path, media_type="image/jpeg")
    else:
        raise HTTPException(status_code=404, detail="Image not found")
    