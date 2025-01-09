import logging.config
from fastapi import Depends, FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks, responses, Security, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import time, os, datetime, io, requests, shutil, tempfile, zipfile
import pandas as pd
from pathlib import Path
from PIL import Image

from . import crud, models, schemas
from .database import SessionLocal, engine

from .dependencies import sentence, gen_image, score, dictionary, openai_chatbot, util
from .authentication import authenticate_user, authenticate_user_2, create_access_token, oauth2_scheme, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, create_refresh_token, REFRESH_TOKEN_EXPIRE_MINUTES, JWTError, jwt
import tracemalloc
tracemalloc.start()

from typing import Tuple, List, Annotated, Optional
from datetime import timezone, timedelta
import torch, stanza
from contextlib import asynccontextmanager
import logging


from .background_tasks import *

models.Base.metadata.create_all(bind=engine)
nlp_models = {}

def model_load():
    util.logger1.info("Loading models: stanza, GPT-2")
    en_nlp = stanza.Pipeline('en', processors='tokenize,pos,constituency', package='default_accurate')
    from transformers import GPT2Tokenizer, GPT2LMHeadModel
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    perplexity_model = GPT2LMHeadModel.from_pretrained("gpt2")
    perplexity_model.eval()
    if torch.cuda.is_available():
        perplexity_model.to('cuda')
    return en_nlp, tokenizer, perplexity_model

nlp_models['en_nlp'], nlp_models['tokenizer'], nlp_models['perplexity_model'] = model_load()

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    await util.logger1.info("Starting up")
    try:
        # Download the English model for stanza
        stanza.download('en')
        nlp_models['en_nlp'], nlp_models['tokenizer'], nlp_models['perplexity_model'] = await model_load()
        util.logger1.info("Models loaded successfully")
        yield
    except Exception as e:
        print(f"Error in lifespan startup: {e}")
        raise
    finally:
        await util.logger1.info("Shutting down")
        await nlp_models.clear()

app = FastAPI(
    debug=True,
    title="AVERY",
    lifespan=lifespan,
)

@app.get("/")
def hello_world():
    return {"message": "Hello World"}

async def get_current_user(db: Annotated[Session, Depends(get_db)],token: Annotated[schemas.TokenData, Depends(oauth2_scheme)]):
#async def get_current_user(db: Annotated[Session, Depends(get_db)],username: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token:
    #if username:
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
    if user.lti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please use Moodle login",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(user.username)
    
    return schemas.Token(access_token=access_token,refresh_token=refresh_token, token_type="bearer")


@app.post("/lti/token",response_model=schemas.Token)
async def login_for_access_token_lti(
    user: schemas.UserLti,
    db: Session = Depends(get_db),
):
    
    user = authenticate_user_2(db, lti_user_id=user.user_id, school=user.school)
    
    if not user.lti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No LTI account found",
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
        util.logger1.error(
            msg=f"Invalid token: {current_user}",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer",
                    "Current User":current_user.username},
        )
    
@app.post("/users/", tags=["User"], response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    user.is_admin=False
    user.user_type="student"
    if user.username=="admin":
        user.is_admin=True
        user.user_type="instructor"
    return crud.create_user(db=db, user=user)

@app.post("/users/lti", tags=["User"], response_model=schemas.User)
def create_user_lti(user: schemas.UserLti, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_lti(db, lti_user_id=user.user_id, school=user.school)
    if db_user:
        raise HTTPException(status_code=400, detail="This account already exists")
    return crud.create_user_lti(db=db, user=user)

@app.delete("/users/{user_id}", tags=["User"], response_model=schemas.UserBase)
def delete_user(current_user: Annotated[schemas.User, Depends(get_current_user)], user_id: int, db: Session = Depends(get_db), ):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to delete user")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return crud.delete_user(db=db, user_id=user_id)

@app.put("/users/{user_id}", tags=["User"], response_model=schemas.User)
def update_user(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    user: schemas.UserUpdateIn,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to update user")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    
    if user.id:
        db_user = crud.get_user(db, user_id=user.id)
    elif user.username:
        db_user = crud.get_user_by_username(db, username=user.username)
    elif user.email:
        db_user = crud.get_user_by_email(db, email=user.email)
    else:
        raise HTTPException(status_code=400, detail="Please provide an id, username, or email")
    
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.id=db_user.id
    user = schemas.UserUpdate(
        **user.model_dump(
            exclude={'email', 'username'},
            exclude_none=True
        )
    )
    return crud.update_user(db=db, user=user)


@app.get("/users/", tags=["User"], response_model=list[schemas.User])
def read_users(current_user: Annotated[schemas.User, Depends(get_current_user)], skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to delete user")
    if current_user.user_type == "student":
        raise HTTPException(status_code=401, detail="You are not allowed to view users")
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@app.get("/users/{user_id}", tags=["User"], response_model=schemas.User)
def read_user(current_user: Annotated[schemas.User, Depends(get_current_user)], user_id: int, db: Session = Depends(get_db)):
    if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(status_code=401, detail="You are not an admin")
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/scenes/", tags=["Scene"], response_model=list[schemas.Scene])
def read_scenes(current_user: Annotated[schemas.User, Depends(get_current_user)], skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to read scenes")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    scenes = crud.get_scenes(db, skip=skip, limit=limit)
    return scenes

@app.post("/scene/", tags=["Scene"], response_model=schemas.Scene)
def create_scene(current_user: Annotated[schemas.User, Depends(get_current_user)], scene: schemas.SceneBase, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to create scene")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    return crud.create_scene(db=db, scene=scene)
    
@app.get("/stories/", tags=["Story"], response_model=list[schemas.StoryOut])
def read_stories(current_user: Annotated[schemas.User, Depends(get_current_user)], skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to read stories")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    stories = crud.get_stories(db, skip=skip, limit=limit)
    return stories
        

@app.post("/story/", tags=["Story"], response_model=schemas.StoryOut)
def create_story(
    current_user: Annotated[schemas.User, Depends(get_current_user)], 
    story_content_file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    scene_id: Annotated[int, Form()],
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to create story")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    
    if not story_content_file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Please upload a text file")
    
    
    try:
        story_content = story_content_file.file.read()
        storyCreate = schemas.StoryCreate(
            title=title,
            scene_id=scene_id,
            content=story_content
        )
                
    except Exception:
        util.logger1.error(f"Error uploading file: {Exception}")
        raise HTTPException(status_code=400, detail="Error uploading file")
    finally:
        story_content_file.file.close()

    return crud.create_story(db=db, story=storyCreate)


@app.get("/leaderboards/", tags=["Leaderboard"], response_model=list[schemas.LeaderboardOut])
def read_leaderboards(current_user: Annotated[schemas.User, Depends(get_current_user)],skip: int = 0, limit: int = 100, published_at_start: str=None, published_at_end: str=None, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view leaderboards")
    school_name = current_user.school
    
    if not published_at_start and not published_at_end:
        leaderboards = crud.get_leaderboards(db, school_name=school_name, skip=skip, limit=limit, published_at_end=datetime.datetime.now(tz=timezone.utc))
        return leaderboards
    
    if published_at_start:
        published_at_start = datetime.datetime.strptime(published_at_start, "%d%m%Y").replace(tzinfo=timezone.utc)
    if published_at_end:
        published_at_end = datetime.datetime.strptime(published_at_end, "%d%m%Y").replace(tzinfo=timezone.utc)
        
    if current_user.user_type == "student":
        if published_at_start and published_at_start > datetime.datetime.now(tz=timezone.utc):
            published_at_start = datetime.datetime.now(tz=timezone.utc)
        if published_at_end and published_at_end > datetime.datetime.now(tz=timezone.utc):
            published_at_end = datetime.datetime.now(tz=timezone.utc)
            
    leaderboards = crud.get_leaderboards(db, school_name=school_name, skip=skip, limit=limit, published_at_start=published_at_start, published_at_end=published_at_end)
    return leaderboards

@app.post("/leaderboards/", tags=["Leaderboard"], response_model=schemas.LeaderboardOut)
def create_leaderboard(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard: schemas.LeaderboardCreateIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to create a leaderboard")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    story_id = leaderboard.story_id
    if story_id==0:
        story_id=None
    
    leaderboard = schemas.LeaderboardCreate(
        **leaderboard.model_dump(),
        created_by_id=current_user.id
    )

    result = crud.create_leaderboard(
        db=db, 
        leaderboard=leaderboard,
    )

    db_story=crud.get_story(db, story_id=story_id)
    if db_story is None:
        story=None
    else:
        story=db_story.content

    db_original_image = crud.get_original_image(db, image_id=leaderboard.original_image_id)

    # add leaderboard vocabularies
    if leaderboard.story_extract:
        words = dictionary.get_sentence_nlp(leaderboard.story_extract)
        for word in words:
            vocab = crud.get_vocabulary(
                db=db,
                vocabulary=word.lemma,
                part_of_speech=word.pos
            )
            if vocab:
                crud.create_leaderboard_vocabulary(
                    db=db,
                    leaderboard_id=result.id,
                    vocabulary_id=vocab.id
                )

    background_tasks.add_task(
        generateDescription,
        db=db,
        leaderboard_id=result.id, 
        image=db_original_image.image, 
        story=story, 
        model_name="gpt-4o-mini"
    )

    return result

@app.post("/leaderboards/bulk_create", tags=["Leaderboard"], response_model=list[schemas.LeaderboardOut])
def create_leaderboards(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    zipped_image_files: Annotated[UploadFile, File()],
    csv_file: Annotated[UploadFile, File()],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Check arguments
    if not zipped_image_files.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a ZIP file")
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to create leaderboards")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    
    if not csv_file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")
    
    # Get the scene
    scene = crud.get_scene(db=db, scene_name="anime")

    # Check leaderboards
    leaderboards = pd.read_csv(csv_file.file)

    # Check if the CSV file has the required columns
    col_names = ['title', 'story_extract']
    if not all(col in leaderboards.columns for col in col_names):
        raise HTTPException(status_code=400, detail="CSV file must have 'title' and 'story_extract' columns")
    
    if 'published_at' in leaderboards.columns:
        leaderboards['published_at'] = pd.to_datetime(leaderboards['published_at'], format='%d/%m/%Y')

    with tempfile.TemporaryDirectory() as temp_dir:

        try:
            # Create a temporary file to store the uploaded content
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                # Copy the uploaded file's content to the temporary file
                shutil.copyfileobj(zipped_image_files.file, tmp)
                
            with zipfile.ZipFile(tmp.name, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error processing uploaded file: {str(e)}"
            )
        finally:
            # Clean up
            import os
            if 'tmp' in locals():
                os.unlink(tmp.name)
    

        images_files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
        if int(len(leaderboards)) != int(len(images_files)):
            raise HTTPException(status_code=400, detail=f"Number of images ({len(images_files)}) and leaderboards ({len(leaderboards)}) do not match")

        # Create images
        try:
            images = {}
            for image_file in images_files:
                try:
                    with open(f'{temp_dir}/{image_file}', 'rb') as f:
                        img = util.encode_image(image_file=f)
                except Exception:
                    raise HTTPException(status_code=400, detail="Please upload a valid image file")

                db_original_image = crud.create_original_image(
                    db=db,
                    image=schemas.ImageBase(
                        image=img
                    )
                )
                title = image_file.split(".")[0]
                images[title] = db_original_image

        except Exception as e:
            util.logger1.error(f"Error creating images: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    # Read the CSV file
    try:
        
        leaderboards.set_index('title', inplace=True)

        # Create leaderboards
        leaderboard_list = []
        for index, row in leaderboards.iterrows():
            
            published_at = row.get('published_at', datetime.datetime.now(tz=timezone.utc))

            if 'story_extract' in leaderboards.columns:
                story_extract = row['story_extract']
            else:
                story_extract = ''

            img = images.get(util.remove_special_chars(index), None)
            if img is None:
                util.logger1.error(f"Image not found: {index}")
                continue

            # Create leaderboard
            leaderboard = schemas.LeaderboardCreate(
                title=index,
                story_extract=story_extract,
                published_at=published_at,
                is_public=True,
                scene_id=scene.id,
                original_image_id=img.id,
                created_by_id=current_user.id,
            )

            db_leaderboard = crud.create_leaderboard(
                db=db,
                leaderboard=leaderboard,
            )

            added_vocabularies = []

            # Add vocabularies
            if story_extract:
                words = dictionary.get_sentence_nlp(story_extract)
                
                for word in words:
                    vocab = crud.get_vocabulary(
                        db=db,
                        vocabulary=word.lemma,
                        part_of_speech=word.pos
                    )
                    if vocab and not crud.get_leaderboard_vocabulary(
                            db=db,
                            leaderboard_id=db_leaderboard.id,
                            vocabulary_id=vocab.id
                    ):
                        crud.create_leaderboard_vocabulary(
                            db=db,
                            leaderboard_id=db_leaderboard.id,
                            vocabulary_id=vocab.id
                        )
                        added_vocabularies.append(vocab.word)

                words = [word.lemma for word in words]

            # Add preset vocabularies
            if 'vocabularies' in leaderboards.columns:
                preset_vocabularies = row['vocabularies']
                preset_vocabularies = preset_vocabularies.split(",")
                preset_vocabularies = [word.strip() for word in preset_vocabularies]
                for word in preset_vocabularies:
                    if word in words:
                        continue
                    vocab = crud.get_vocabulary(
                        db=db,
                        vocabulary=word
                    )
                    if not vocab:
                        continue
                    while vocab:
                        v = vocab.pop()
                        lv = crud.get_leaderboard_vocabulary(
                            db=db,
                            leaderboard_id=db_leaderboard.id,
                            vocabulary_id=v.id
                        )
                        if lv:
                            break
                    if lv:
                        continue
                    crud.create_leaderboard_vocabulary(
                        db=db,
                        leaderboard_id=db_leaderboard.id,
                        vocabulary_id=v.id
                    )
                    added_vocabularies.append(v.word)

                # Log the difference between the added and preset vocabularies
                diff = set(added_vocabularies) - set(preset_vocabularies)
                if diff:
                    util.logger1.info(f"Leaderboard {index} Added vocabularies: {diff}")
            leaderboard_list.append(db_leaderboard)

            # Generate descriptions
            background_tasks.add_task(
                generateDescription,
                db=db,
                leaderboard_id=db_leaderboard.id, 
                image=img.image, 
                story=story_extract, 
                model_name="gpt-4o-mini"
            )

        # Remove the temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        return leaderboard_list

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV file: {str(e)}")

@app.post("/leaderboards/image", tags=["Leaderboard"], response_model=schemas.IdOnly)
def create_leaderboard_image(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    original_image: Annotated[UploadFile, File()],
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to upload image")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")

    try:
        original_image.file.seek(0)
        img = util.encode_image(image_file=original_image.file)
    except Exception:
        raise HTTPException(status_code=400, detail="Please upload a valid image file")
    finally:
        original_image.file.close()
        
    db_original_image = crud.create_original_image(
        db=db,
        image=schemas.ImageBase(
            image=img
        )
    )

    return db_original_image

@app.get("/leaderboards/{leaderboard_id}", tags=["Leaderboard"], response_model=schemas.LeaderboardOut)
def read_leaderboard(current_user: Annotated[schemas.User, Depends(get_current_user)],leaderboard_id: int, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view leaderboards")
    db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
    if db_leaderboard is None:
        util.logger1.error(f"Leaderboard not found: {leaderboard_id}")
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    return db_leaderboard

@app.put("/leaderboards/{leaderboard_id}", tags=["Leaderboard"], response_model=schemas.LeaderboardOut)
def update_leaderboard(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard_id: int,
    leaderboard: schemas.LeaderboardUpdate,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to update leaderboard")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
    if db_leaderboard is None:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    return crud.update_leaderboard(db=db, leaderboard=leaderboard)

@app.delete("/leaderboards/{leaderboard_id}", tags=["Leaderboard"], response_model=schemas.IdOnly)
def delete_leaderboard(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard_id: int,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to delete leaderboard")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
    if db_leaderboard is None:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    return crud.delete_leaderboard(db=db, leaderboard_id=leaderboard_id)

@app.post("/program", tags=["Program"], response_model=schemas.Program)
def create_program(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    program: schemas.ProgramBase,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to create program")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    return crud.create_program(db=db, program=program)

@app.get("/programs/", tags=["Program"], response_model=list[schemas.Program])
def read_programs(current_user: Annotated[schemas.User, Depends(get_current_user)], skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to read programs")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    programs = crud.get_programs(db, skip=skip, limit=limit)
    return programs

@app.get("/leaderboards/{leaderboard_id}/rounds/", tags=["Leaderboard", "Round"], response_model=list[schemas.RoundOut])
def get_rounds_by_leaderboard(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard_id: int,
    program: Optional[str] = "none",
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view")
    
    if program == "none":
        return []
    elif program == "overview":
        return crud.get_rounds(
            db=db,
            leaderboard_id=leaderboard_id,
        )
    db_program = crud.get_program_by_name(db, program)
    return crud.get_rounds(
        db=db,
        leaderboard_id=leaderboard_id,
        program_id=db_program.id
    )

@app.get("/my_rounds/", tags=["Round"], response_model=list[schemas.RoundOut])
def get_my_rounds(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard_id: Optional[int] = None,
    is_completed: Optional[bool] = True,
    db: Session = Depends(get_db),
):
    if not current_user:
        return []
    player_id = current_user.id
    return crud.get_rounds(
        db=db,
        is_completed=is_completed,
        player_id=player_id,
        leaderboard_id=leaderboard_id,
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
        status, correct_sentence=sentence.checkSentence(passage=db_generation.sentence)

    except Exception as e:
        util.logger1.error(f"Error in get_user_answer: {str(e)}")
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
            chat_id=db_round.chat_history
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
    raise HTTPException(status_code=400, detail="Invalid sentence")

@app.put("/round/{round_id}/interpretation", tags=["Round"], response_model=schemas.GenerationInterpretation)
async def get_interpretation(
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
    
    db_generation = crud.get_generation(db, generation_id=generation.id)

    try:
        # Image generation
        gen_img_tracker = util.computing_time_tracker(message="Image generation started - DALLE 3")
        interpreted_image_url = gen_image.generate_interpretion(
            sentence=db_generation.sentence,
        )
        gen_img_tracker.stop_timer()

        # Download and save image
        try:
            b_interpreted_image = io.BytesIO(requests.get(interpreted_image_url).content)
            image = util.encode_image(image_file=b_interpreted_image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
        
        # Database operations
        db_interpreted_image = crud.create_interpreted_image(
            db=db,
            image=schemas.ImageBase(
                image=image,
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

        # Get descriptions
        descriptions =  crud.get_description(db, leaderboard_id=db_round.leaderboard_id, model_name=db_round.model)
        descriptions = [des.content for des in descriptions]

        # Safe background task addition with error handling
        try:

            # if 'en_nlp' not in nlp_models or 'perplexity_model' not in nlp_models or 'tokenizer' not in nlp_models:
            #     nlp_models['en_nlp'], nlp_models['tokenizer'], nlp_models['perplexity_model'] = model_load()

            # Update scores in background
            background_tasks.add_task(
                update_perplexity,
                db=db,
                en_nlp=nlp_models['en_nlp'],
                perplexity_model=nlp_models['perplexity_model'],
                tokenizer=nlp_models['tokenizer'],
                generation=generation_complete,
                descriptions=descriptions
            )
            
            background_tasks.add_task(
                update_content_score,
                db=db,
                generation=generation_complete
            )

            # background_tasks.add_task(
            #     update_frequency_word,
            #     db=db,
            #     en_nlp=nlp_models['en_nlp'],
            #     generation=generation_complete
            # )

            background_tasks.add_task(
                update_n_words,
                db=db,
                en_nlp=nlp_models['en_nlp'],
                generation=generation_complete
            )
        except Exception as e:
            # Log the background task error without raising
            util.logger1.error(f"Error in background task addition: {str(e)}")

        # Get round and create message
        db_round = crud.get_round(db, round_id)

        new_message = """回答をシステム入力しました。📝
回答: {}\n\n修正された回答：{}""".format(db_generation.sentence, db_generation.correct_sentence)

        crud.create_message(
            db=db,
            message=schemas.MessageBase(
                content=new_message,
                sender="assistant",
                created_at=datetime.datetime.now(tz=timezone.utc)
            ),
            chat_id=db_round.chat_history
        )

        return db_generation

    except HTTPException:
        # Re-raise HTTP exceptions
        raise HTTPException(status_code=400, detail="Invalid image file")
    except Exception as e:
        # Catch and log any unexpected errors
        util.logger1.error(f"Unexpected error in get_interpretation: {str(e)}")
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
    
    db_chat = crud.get_chat(db=db,chat_id=db_round.chat_history)
    cb=openai_chatbot.Hint_Chatbot()

    # if 'en_nlp' not in nlp_models or 'perplexity_model' not in nlp_models or 'tokenizer' not in nlp_models:
    #     nlp_models['en_nlp'], nlp_models['tokenizer'], nlp_models['perplexity_model'] = model_load()

    factors, scores_dict = calculate_score(
        db=db,
        en_nlp=nlp_models['en_nlp'],
        perplexity_model=nlp_models['perplexity_model'],
        tokenizer=nlp_models['tokenizer'],
        generation=generation,
        is_completed=True,
    )
    if 'grammar_error' in factors:
        grammar_errors=str(factors['grammar_error'])
        spelling_errors=str(factors['spelling_error'])
    elif factors['n_grammar_errors'] > 0:
        errors = score.grammar_spelling_errors(db_generation.sentence, en_nlp=nlp_models['en_nlp'])
        grammar_errors=str(errors['grammar_error'])
        spelling_errors=str(errors['spelling_error'])
    else:
        grammar_errors='None'
        spelling_errors='None'

    evaluation = cb.get_result(
        sentence=db_generation.sentence,
        correct_sentence=db_generation.correct_sentence,
        scoring=scores_dict,
        rank=db_generation.rank,
        base64_image=db_round.leaderboard.original_image.image,
        chat_history=db_chat.messages,
        grammar_errors=grammar_errors,
        spelling_errors=spelling_errors
    )

    if evaluation:
        score_message = """あなたの回答：{user_sentence}
修正された回答：{correct_sentence}
文法得点: {grammar_score} (満点5)
スペリング得点: {spelling_score} (満点5)
鮮明さ: {vividness_score} (満点5)
自然さ: {convention} (満点1)
構造性: {structure_score} (満点3)
内容得点: {content_score} (満点100)
合計点: {total_score} (満点100)
ランク: {rank}　(A-最高, B-上手, C-良い, D-普通, E-悪い, F-最悪)
        """.format(
            user_sentence=db_generation.sentence,
            correct_sentence=db_generation.correct_sentence,
            grammar_score=round(scores_dict['grammar_score'],2),
            spelling_score=round(scores_dict['spelling_score'],2),
            vividness_score=round(scores_dict['vividness_score'],2),
            convention=scores_dict['convention'],
            structure_score=scores_dict['structure_score'],
            content_score=scores_dict['content_score'],
            total_score=scores_dict['total_score'],
            rank=db_generation.rank,
        )

        evaluation_message = """**文法**
{grammar_feedback}
**スペル**
{spelling_feedback}
**スタオル**
{style_feedback}
**内容**
{content_feedback}

**整体的なコメント**
{overall_feedback}
        """.format(
            grammar_feedback=evaluation.grammar_evaluation,
            spelling_feedback=evaluation.spelling_evaluation,
            style_feedback=evaluation.style_evaluation,
            content_feedback=evaluation.content_evaluation,
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

        crud.create_score(
            db=db,
            score=schemas.ScoreCreate(
                generation_id=generation.id,
                grammar_score=scores_dict['grammar_score'],
                spelling_score=scores_dict['spelling_score'],
                vividness_score=scores_dict['vividness_score'],
                convention=scores_dict['convention'],
                structure_score=scores_dict['structure_score'],
                content_score=scores_dict['content_score'],
            ),
            generation_id=generation.id
        )

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

@app.get("/vocabulary/{vocabulary}", tags=["Vocabulary"], response_model=list[schemas.Vocabulary])
def read_vocabulary(current_user: Annotated[schemas.User, Depends(get_current_user)], vocabulary: str, pos: str=None, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view vocabulary")
    if pos:
        vocabularies = [crud.get_vocabulary(db, vocabulary=vocabulary, part_of_speech=pos)]
    else:
        vocabularies = crud.get_vocabulary(db, vocabulary=vocabulary)
    if not vocabularies:
        raise HTTPException(status_code=404, detail="Vocabulary not found")
    return vocabularies

@app.get("/vocabularies/", tags=["Vocabulary"], response_model=list[schemas.Vocabulary])
def read_vocabularies(current_user: Annotated[schemas.User, Depends(get_current_user)], skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view vocabularies")
    vocabularies = crud.get_vocabularies(db, skip=skip, limit=limit)
    return vocabularies

@app.post("/vocabularies", tags=["Vocabulary"], response_model=List[schemas.Vocabulary])
def create_vocabularies(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    vocabularies_csv: Annotated[UploadFile, File()],
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to create vocabulary")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    
    if not vocabularies_csv.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")
    
    output = []
    try:
        vocabularies = pd.read_csv(vocabularies_csv.file)
        col_names = ['word','pos']
        if not all(col in vocabularies.columns for col in col_names):
            raise HTTPException(status_code=400, detail="CSV file must have 'word' and 'pos' columns")
        
        for index, row in vocabularies.iterrows():
            pos = row['pos'].split(",")
            for p in pos:
                p = p.strip()

                meaning = dictionary.get_meaning(
                    lemma=row['word'],
                    pos=p
                )

                if isinstance(meaning, list):
                    meaning = '; '.join(meaning)
                elif meaning is None:
                    continue
                elif meaning == "Word not found in the dictionary":
                    continue
                
                v = crud.create_vocabulary(
                    db=db,
                    vocabulary=schemas.VocabularyBase(
                        word=row['word'],
                        pos=p,
                        meaning=meaning
                    )
                )
                output.append(v)
        return output
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    round_id: int, 
    db: Session = Depends(get_db),
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

    vocabularies = db_round.leaderboard.vocabularies
    # get hint from AI
    cb = openai_chatbot.Hint_Chatbot(vocabularies=vocabularies)

    model_response = cb.nextResponse(
        ask_for_hint=message.content,
        chat_history=db_chat.messages,
        base64_image=db_round.leaderboard.original_image.image,
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

    #decode base64 image
    if db_leaderboard.original_image is None:
        raise HTTPException(status_code=404, detail="Original image not found")
    
    imgdata = util.decode_image(db_leaderboard.original_image.image)
    return responses.Response(
        content=imgdata,
        media_type="image/jpeg"  # Adjust this based on your image type (jpeg, png, etc.)
    )
    
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

    # if current_user.id != db_round.player_id and not current_user.is_admin:
    #     raise HTTPException(status_code=401, detail="You are not authorized to view images")
    if db_generation.interpreted_image is None:
        raise HTTPException(status_code=404, detail="Interpreted image not found")
    
    imgdata = util.decode_image(db_generation.interpreted_image.image)
    return responses.Response(
        content=imgdata,
        media_type="image/jpeg"  # Adjust this based on your image type (jpeg, png, etc.)
    )
    
@app.get("/image_similarity/{generation_id}", tags=["Image"], response_model=schemas.ImageSimilarity)
def get_image_similarity(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    generation_id: int, 
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to get image similarity")
    
    db_generation = crud.get_generation(
        db=db,
        generation_id=generation_id
    )

    db_round = crud.get_round(
        db=db,
        round_id=db_generation.round_id
    )

    # if current_user.id != db_round.player_id and not current_user.is_admin:
    #     raise HTTPException(status_code=401, detail="You are not authorized to view images")

    db_leaderboard = crud.get_leaderboard(
        db=db,
        leaderboard_id=db_round.leaderboard_id
    )

    semantic1 = score.calculate_content_score(
        image=db_leaderboard.original_image.image,
        sentence=db_generation.sentence
    )

    semantic2 = score.calculate_content_score(
        image=db_generation.interpreted_image.image,
        sentence=db_generation.sentence
    )

    denominator = semantic1['content_score']+semantic2['content_score']
    if denominator == 0:
        blip2_score = 0
    else:
        blip2_score = abs(semantic1['content_score'] - semantic2['content_score'])/(semantic1['content_score']+semantic2['content_score'])
        blip2_score = 1 - blip2_score

    ssim = score.image_similarity(
        image1=db_leaderboard.original_image.image,
        image2=db_generation.interpreted_image.image
    )["ssim_score"]

    similarity = blip2_score*0.8 + ssim*0.2

    image_similarity = schemas.ImageSimilarity(
        semantic_score_original=semantic1['content_score'],
        semantic_score_interpreted=semantic2['content_score'],
        blip2_score=blip2_score,
        ssim=ssim,
        similarity=similarity

    )

    score_id = db_generation.score_id
    if score_id is not None:
        crud.update_score(
            db=db,
            score=schemas.ScoreUpdate(
                id=score_id,
                image_similarity=similarity
            )
        )

    return image_similarity

@app.get("/generation/{generation_id}", tags=["Generation"], response_model=schemas.GenerationOut)
def read_generation(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    generation_id: int, 
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view generation")
    db_generation = crud.get_generation(
        db=db,
        generation_id=generation_id
    )
    if db_generation is None:
        raise HTTPException(status_code=404, detail="Generation not found")
    return db_generation

@app.get("/generations/", tags=["Generation"], response_model=list[Tuple[schemas.GenerationOut, schemas.RoundOut]])
def read_generations(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    player_id: Optional[int] = None,
    leaderboard_id: Optional[int] = None,
    school_name: Optional[str] = None,
    program: Optional[str] = None,
    order_by: Optional[str] = "total_score",
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view generations")
    if player_id != current_user.id and current_user.user_type == "student":
        raise HTTPException(status_code=401, detail="You are not authorized to view generations")
    if player_id is None and current_user.user_type == "student":
        player_id = current_user.id

    if program == "none":
        return []
    elif program == "overview":
        generations = crud.get_generations(
            db=db,
            skip=skip,
            limit=limit,
            player_id=player_id,
            leaderboard_id=leaderboard_id,
            order_by=order_by
        )
        
        if school_name:
            generations = [gen for gen in generations if gen[1].player.school_name == school_name]

        return generations
    db_program = crud.get_program_by_name(db, program)
    if db_program is None:
        raise HTTPException(status_code=404, detail="Program not found")
    generations = crud.get_generations(
        db=db,
        program_id=db_program.id,
        skip=skip,
        limit=limit,
        player_id=player_id,
        leaderboard_id=leaderboard_id,
        order_by=order_by
    )
    return generations

@app.get("/generation/{generation_id}/score", tags=["Generation"], response_model=schemas.Score)
def get_generation_score(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    generation_id: int, 
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view generation")
    db_generation = crud.get_generation(
        db=db,
        generation_id=generation_id
    )
    if db_generation is None:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    score = crud.get_score(
        db=db,
        generation_id=generation_id
    )
    return score

@app.get("/leaderboards/{leaderboard_id}/playable", tags=["Leaderboard"], response_model=schemas.LeaderboardPlayable)
def check_leaderboard_playable(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard_id: int, 
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to check leaderboard")
    
    if not current_user.is_admin:
        db_rounds = crud.get_rounds(
            db=db,
            leaderboard_id=leaderboard_id,
            player_id=current_user.id
        )

        if db_rounds:
            return schemas.LeaderboardPlayable(
                id=leaderboard_id,
                is_playable=False
            )
    
    return schemas.LeaderboardPlayable(
        id=leaderboard_id,
        is_playable=True
    )