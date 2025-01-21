import logging.config
from fastapi import Depends, FastAPI, HTTPException, File, UploadFile, Form, responses, Security, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import time, os, datetime, shutil, tempfile, zipfile, zoneinfo, asyncio
import pandas as pd
from pathlib import Path

from . import crud, models, schemas
from .tasks import app as celery_app
from .tasks import check_factors_done, check_factors_done_by_dict, generateDescription, update_vocab_used_time, generate_interpretation, pass_generation_dict, update_perplexity, update_content_score, update_frequency_word, update_n_words, update_grammar_spelling, cal_image_similarity, calculate_score
from .database import SessionLocal, engine

from .dependencies import sentence, score, dictionary, openai_chatbot, util
from .authentication import authenticate_user, authenticate_user_2, create_access_token, oauth2_scheme, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, create_refresh_token, REFRESH_TOKEN_EXPIRE_MINUTES, JWTError, jwt

from typing import Tuple, List, Annotated, Optional
from datetime import timezone, timedelta
from contextlib import asynccontextmanager
from celery import chain, group
import logging

models.Base.metadata.create_all(bind=engine)
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
        import stanza
        stanza.download('en')
        # nlp_models['en_nlp'], nlp_models['tokenizer'], nlp_models['perplexity_model'] = await model_load()
        # util.logger1.info("Models loaded successfully")
        util.logger1.info("Startup complete")
        yield
    except Exception as e:
        print(f"Error in lifespan startup: {e}")
        raise
    finally:
        await util.logger1.info("Shutting down")
        # await nlp_models.clear()
        with get_db() as db:
            await crud.delete_all_tasks(db=db)

app = FastAPI(
    debug=True,
    title="AVERY",
    lifespan=lifespan,
)

@app.get("/")
def hello_world():
    return {"Hello": "World"}

@app.get("/tasks", tags=["Task"], response_model=list[schemas.Task])
async def read_tasks(
    db: Session = Depends(get_db),
):
    return crud.get_all_tasks(db)

@app.get("/tasks/{task_id}", tags=["Task"], response_model=schemas.TaskStatus)
async def check_status(
    task_id: str, 
    db: Session = Depends(get_db)
):
    result = celery_app.AsyncResult(task_id)
    status = schemas.TaskStatus(
        id=task_id,
        status=result.status,
        result=result.result
    )
    if result.status == "SUCCESS":
        crud.delete_task(db, task_id)
    return status

@app.get("/tasks/generation/{generation_id}", tags=["Task"], response_model=schemas.TasksOut)
async def check_generation_task_status(
    generation_id: int, 
):
    return check_factors_done(generation_id)

@app.get("/tasks/leaderboard/{leaderboard_id}", tags=["Task"], response_model=list[schemas.TaskStatus])
async def check_leaderboard_task_status(
    leaderboard_id: int, 
    db: Session = Depends(get_db)
):
    celery_tasks = crud.get_tasks(db, leaderboard_id=leaderboard_id)
    output = []
    for t in celery_tasks:
        result = celery_app.AsyncResult(t.task_id)
        output.append(
            schemas.TaskStatus(
                id=t.task_id,
                status=result.status,
                result=result.result
            )
        )
        if result.status == "SUCCESS":
            crud.delete_task(db, t.task_id)

    return output

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
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
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
async def create_user_lti(user: schemas.UserLti, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_lti(db, lti_user_id=user.user_id, school=user.school)
    if db_user:
        raise HTTPException(status_code=400, detail="This account already exists")
    return crud.create_user_lti(db=db, user=user)

@app.delete("/users/{user_id}", tags=["User"], response_model=schemas.UserBase)
async def delete_user(current_user: Annotated[schemas.User, Depends(get_current_user)], user_id: int, db: Session = Depends(get_db), ):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to delete user")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return crud.delete_user(db=db, user_id=user_id)

@app.put("/users/{user_id}", tags=["User"], response_model=schemas.User)
async def update_user(
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
async def read_users(current_user: Annotated[schemas.User, Depends(get_current_user)], skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to delete user")
    if current_user.user_type == "student":
        raise HTTPException(status_code=401, detail="You are not allowed to view users")
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@app.get("/users/{user_id}", tags=["User"], response_model=schemas.User)
async def read_user(current_user: Annotated[schemas.User, Depends(get_current_user)], user_id: int, db: Session = Depends(get_db)):
    if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(status_code=401, detail="You are not an admin")
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/scenes/", tags=["Scene"], response_model=list[schemas.Scene])
async def read_scenes(current_user: Annotated[schemas.User, Depends(get_current_user)], skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to read scenes")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    scenes = crud.get_scenes(db, skip=skip, limit=limit)
    return scenes

@app.post("/scene/", tags=["Scene"], response_model=schemas.Scene)
async def create_scene(current_user: Annotated[schemas.User, Depends(get_current_user)], scene: schemas.SceneBase, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to create scene")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    return crud.create_scene(db=db, scene=scene)
    
@app.get("/stories/", tags=["Story"], response_model=list[schemas.StoryOut])
async def read_stories(current_user: Annotated[schemas.User, Depends(get_current_user)], skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to read stories")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    stories = crud.get_stories(db, skip=skip, limit=limit)
    return stories
        

@app.post("/story/", tags=["Story"], response_model=schemas.StoryOut)
async def create_story(
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


@app.get("/leaderboards/", tags=["Leaderboard"], response_model=list[Tuple[schemas.LeaderboardOut, schemas.SchoolOut]])
async def read_leaderboards(current_user: Annotated[schemas.User, Depends(get_current_user)],skip: int = 0, limit: int = 100, published_at_start: str=None, published_at_end: str=None, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view leaderboards")
    school_name = current_user.school
    
    if not published_at_start and not published_at_end:
        leaderboards = crud.get_leaderboards(db, school_name=school_name, skip=skip, limit=limit, published_at_end=datetime.datetime.now(tz=zoneinfo.ZoneInfo('Japan')))
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

@app.get("/leaderboards/admin/", tags=["Leaderboard"], response_model=list[schemas.LeaderboardOut])
async def read_leaderboards_admin(
        current_user: Annotated[schemas.User, Depends(get_current_user)],
        skip: int = 0,
        limit: int = 100,
        published_at_start: str = None,
        published_at_end: str = None,
        db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view leaderboards")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    
    if published_at_start:
        published_at_start = datetime.datetime.strptime(published_at_start, "%d%m%Y").replace(tzinfo=timezone.utc)
    if published_at_end:
        published_at_end = datetime.datetime.strptime(published_at_end, "%d%m%Y").replace(tzinfo=timezone.utc)

    leaderboards = crud.get_leaderboards_admin(
        db=db,
        skip=skip,
        limit=limit,
        published_at_start=published_at_start,
        published_at_end=published_at_end,
    )
    return leaderboards

@app.post("/leaderboards/", tags=["Leaderboard"], response_model=schemas.LeaderboardOut)
async def create_leaderboard(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard: schemas.LeaderboardCreateIn,
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
    en_nlp = dictionary.Dictionary()
    # add leaderboard vocabularies
    if leaderboard.story_extract:
        words = en_nlp.get_sentence_nlp(leaderboard.story_extract)
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

    t = generateDescription.delay(
        leaderboard_id=result.id, 
        image=db_original_image.image, 
        story=story, 
        model_name="gpt-4o-mini"
    )

    crud.create_task(
        db=db,
        task=schemas.Task(
            task_id=t.id,
            leaderboard_id=result.id,
        )
    )

    return result

@app.post("/leaderboards/bulk_create", tags=["Leaderboard"], response_model=list[schemas.LeaderboardOut])
async def create_leaderboards(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    zipped_image_files: Annotated[UploadFile, File()],
    csv_file: Annotated[UploadFile, File()],
    school: Optional[str] = None,
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

            if 'id' in leaderboards.columns:
                img_title = str(row['id']) + ' ' + index
            else:
                img_title = index
            img = images.get(util.remove_special_chars(img_title), None)

            if img is None:
                util.logger1.error(f"Image not found: {img_title}")
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

            en_nlp = dictionary.Dictionary()

            # Add vocabularies
            if story_extract:
                words = en_nlp.get_sentence_nlp(story_extract)
                
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
            
            # Add school
            if school:
                crud.update_leaderboard(
                    db=db,
                    leaderboard=schemas.LeaderboardUpdate(
                        id=db_leaderboard.id,
                        school=[school],
                        vocabularies=[]
                    )
                )
            
            leaderboard_list.append(db_leaderboard)

            # Generate description
            t = generateDescription.delay(
                leaderboard_id=db_leaderboard.id, 
                image=img.image, 
                story=story_extract, 
                model_name="gpt-4o-mini"
            )
            crud.create_task(
                db=db,
                task=schemas.Task(
                    id=t.id,
                    leaderboard_id=db_leaderboard.id,
                )
            )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV file: {str(e)}")

    # Remove the temporary directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    return leaderboard_list

@app.post("/leaderboards/image", tags=["Leaderboard"], response_model=schemas.IdOnly)
async def create_leaderboard_image(
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
async def read_leaderboard(current_user: Annotated[schemas.User, Depends(get_current_user)],leaderboard_id: int, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view leaderboards")
    db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
    if db_leaderboard is None:
        util.logger1.error(f"Leaderboard not found: {leaderboard_id}")
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    return db_leaderboard

@app.get("/leaderboards/{leaderboard_id}/schools/", tags=["Leaderboard"], response_model=list[schemas.SchoolOut])
async def read_schools(current_user: Annotated[schemas.User, Depends(get_current_user)], leaderboard_id: int, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view schools")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    schools = crud.get_school_leaderboard(db, leaderboard_id=leaderboard_id)
    return schools

@app.put("/leaderboards/{leaderboard_id}", tags=["Leaderboard"], response_model=schemas.LeaderboardOut)
async def update_leaderboard(
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
async def delete_leaderboard(
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
async def create_program(
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
async def read_programs(current_user: Annotated[schemas.User, Depends(get_current_user)], skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to read programs")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    programs = crud.get_programs(db, skip=skip, limit=limit)
    return programs

@app.get("/leaderboards/{leaderboard_id}/rounds/", tags=["Leaderboard", "Round"], response_model=list[schemas.RoundOut])
async def get_rounds_by_leaderboard(
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
async def get_my_rounds(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard_id: Optional[int] = None,
    is_completed: Optional[bool] = True,
    program: Optional[str] = "none",
    db: Session = Depends(get_db),
):
    if not current_user:
        return []
    player_id = current_user.id

    if program != "none" and program != "overview":
        db_program = crud.get_program_by_name(db, program)
        if db_program:
            return crud.get_rounds(
                db=db,
                is_completed=is_completed,
                player_id=player_id,
                leaderboard_id=leaderboard_id,
                program_id=db_program.id
            )

    return crud.get_rounds(
        db=db,
        is_completed=is_completed,
        player_id=player_id,
        leaderboard_id=leaderboard_id,
    )

@app.post("/round/", tags=["Round"], response_model=schemas.Round)
async def create_round(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    thisround: schemas.RoundCreate,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to create a round")
    player_id = current_user.id

    db_program = crud.get_program_by_name(db, thisround.program)
    if db_program is None:
        db_round = crud.create_round(
            db=db,
            leaderboard_id=thisround.leaderboard_id,
            user_id=player_id,
            model_name=thisround.model,
            created_at=thisround.created_at,
        )      
    else:  
        db_round = crud.create_round(
            db=db,
            leaderboard_id=thisround.leaderboard_id,
            user_id=player_id,
            model_name=thisround.model,
            created_at=thisround.created_at,
            program_id=db_program.id
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
async def get_user_answer(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    round_id: int,
    generation: schemas.GenerationCreate,
    db: Session = Depends(get_db),
):
    mem_track = util.memory_tracker(message="Get user answer", id=round_id)
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to answer")
    db_round = crud.get_round(db, round_id)
    if current_user.id != db_round.player_id:
        raise HTTPException(status_code=401, detail="You are not authorized to answer")
    db_generation = crud.get_generation(db, generation_id=db_round.last_generation_id)
    if db_generation and not db_generation.is_completed:
        db_generation = crud.update_generation0(
            db=db,
            generation=generation,
            generation_id=db_generation.id
        )
    else:
        db_generation = crud.create_generation(
            db=db,
            round_id=round_id,
            generation=generation,
        )
 
    try:
        status, correct_sentence, spelling_mistakes, grammar_mistakes=sentence.checkSentence(passage=db_generation.sentence)

    except Exception as e:
        util.logger1.error(f"Error in get_user_answer: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    db_round = crud.get_round(db, round_id)

    update_vocab_used_time.delay(
        sentence=db_generation.sentence,
        user_id=db_round.player_id
    )

    if status == 0:
        crud.update_generation3(
            db=db,
            generation=schemas.GenerationComplete(
                id=db_generation.id,
                grammar_errors=str(grammar_mistakes),
                spelling_errors=str(spelling_mistakes),
                n_grammar_errors=len(grammar_mistakes),
                n_spelling_errors=len(spelling_mistakes),
                updated_grammar_errors=True,
                is_completed=False
            )
        )
        mem_track.get_top_stats()
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
    mem_track.get_top_stats()
    raise HTTPException(status_code=400, detail="Invalid sentence")

@app.put("/round/{round_id}/interpretation", tags=["Round"], response_model=schemas.IdOnly)
async def get_interpretation(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    round_id: int,
    generation: schemas.GenerationCorrectSentence,
    db: Session = Depends(get_db),
):
    mem_track = util.memory_tracker(message="Get interpretation", id=generation.id)
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to get interpretation")
    db_round = crud.get_round(db, round_id)
    if current_user.id != db_round.player_id:
        raise HTTPException(status_code=401, detail="You are not authorized to get interpretation")
    
    db_generation = crud.get_generation(db, generation_id=generation.id)

    try:
        # Check if description generation is done
        leaderboard_tasks = await check_leaderboard_task_status(
            db=db,
            leaderboard_id=db_round.leaderboard_id,
        )
        
        if leaderboard_tasks:
            while not all([t.status == "SUCCESS" for t in leaderboard_tasks]):
                await asyncio.sleep(1)
                leaderboard_tasks = await check_leaderboard_task_status(
                    db=db,
                    leaderboard_id=db_round.leaderboard_id,
                )    

        # Safe background task addition with error handling
        try:
            if db_generation.interpreted_image_id is None:
                factors_done = check_factors_done(
                    generation_id=generation.id
                )
                if factors_done["status"] == "FINISHED":
                    return db_generation
                
            generation_dict = {
                "id": generation.id,
                "at": db_generation.created_at,
            }

            chain_interpretation = chain(
                group(
                    generate_interpretation.s(generation_id=generation.id, sentence=db_generation.sentence, at=db_generation.created_at),
                    update_content_score.s(generation=generation_dict),
                    update_n_words.s(generation=generation_dict),
                    update_grammar_spelling.s(generation=generation_dict),
                    #update_frequency_word.s(generation=generation_dict),
                    update_perplexity.s(generation=generation_dict),
                ),
                group(
                    pass_generation_dict.s(),
                ),
                group(
                    check_factors_done_by_dict.s()
                ),
                group(
                    pass_generation_dict.s(),
                    calculate_score.s()
                ),
                cal_image_similarity.s(),
            )
            chain_interpretation.apply_async()

        except Exception as e:
            # Log the background task error without raising
            util.logger1.error(f"Error in background task addition: {str(e)}")

        # Get round and create message
        db_round = crud.get_round(db, round_id)

        new_message = """回答をシステム入力しました。📝
あなたの回答（画像生成に参考された）: {}\n\n修正された回答：{}""".format(db_generation.sentence, db_generation.correct_sentence)

        crud.create_message(
            db=db,
            message=schemas.MessageBase(
                content=new_message,
                sender="assistant",
                created_at=datetime.datetime.now(tz=timezone.utc)
            ),
            chat_id=db_round.chat_history
        )

        mem_track.get_top_stats()
        return db_generation

    except HTTPException:
        # Re-raise HTTP exceptions
        raise HTTPException(status_code=400, detail="Invalid image file")
    except Exception as e:
        # Catch and log any unexpected errors
        util.logger1.error(f"Unexpected error in get_interpretation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/round/{round_id}/complete", tags=["Round"], response_model=schemas.GenerationComplete)
async def complete_generation(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    generation: schemas.GenerationCompleteCreate,
    db: Session = Depends(get_db),
):
    mem_track = util.memory_tracker(message="Complete generation",id=generation.id)
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

    # Check if the score calculation is done
    timeout = time.time() + 60
    counter=0

    factors = check_factors_done(
        generation_id=generation.id
    )

    if factors["status"] != "FINISHED":
        while time.time() < timeout:
            factors = check_factors_done(
                generation_id=generation.id
            )
            if factors["status"] == "FINISHED":
                break
            await asyncio.sleep(3)
            counter+=1
            if counter>30:
                raise HTTPException(status_code=400, detail="Timeout error")
            raise HTTPException(status_code=400, detail="Error in score calculation")
        
    factors, scores_dict = calculate_score(
        generation=generation.model_dump(),
        is_completed=True,
    )

    db_generation = crud.get_generation(db, generation_id=generation.id)
    descriptions = crud.get_description(db, leaderboard_id=db_round.leaderboard_id, model_name=db_round.model)
    descriptions = [des.content for des in descriptions]

    evaluation = cb.get_result(
        sentence=db_generation.sentence,
        correct_sentence=db_generation.correct_sentence,
        scoring=scores_dict,
        rank=db_generation.rank,
        base64_image=db_round.leaderboard.original_image.image,
        chat_history=db_chat.messages,
        grammar_errors=db_generation.grammar_errors,
        spelling_errors=db_generation.spelling_errors,
        descriptions=descriptions
    )

    if evaluation:
        score_message = """あなたの回答（評価対象）：{user_sentence}

修正された回答　　　　 ：{correct_sentence}


| 　　          | 得点   | 満点       |
|---------------|--------|------|
| 文法得点      |{:>5}|  5  |
| スペリング得点|{:>5}|  5  |
| 鮮明さ        |{:>5}|  5  |
| 自然さ        |{:>5}|  1  |
| 構造性        |{:>5}|  3  |
| 内容得点      |{:>5}| 100 |
| 合計点        |{:>5}| 100 |
| ランク        |{:>5}|(A-最高, B-上手, C-良い, D-普通, E-もう少し, F-頑張ろう)|""".format(
            round(scores_dict['grammar_score'],2),
            round(scores_dict['spelling_score'],2),
            round(scores_dict['vividness_score'],2),
            scores_dict['convention'],
            scores_dict['structure_score'],
            scores_dict['content_score'],
            scores_dict['total_score'],
            db_generation.rank,
            user_sentence=db_generation.sentence,
            correct_sentence=db_generation.correct_sentence,
        )

        if len(db_round.generations) > 2:
            recommended_vocabs = db_round.leaderboard.vocabularies
            recommended_vocabs = [vocab.word for vocab in recommended_vocabs]
            recommended_vocab = "\n\n**おすすめの単語**\n" + ", ".join(recommended_vocabs)
        else:
            recommended_vocab = ""

        evaluation_message = """**文法**
{grammar_feedback}
**スペル**
{spelling_feedback}
**スタイル**
{style_feedback}
**内容**
{content_feedback}

**総合評価**
{overall_feedback}{recommended_vocab}""". \
        format(
            grammar_feedback=evaluation.grammar_evaluation,
            spelling_feedback=evaluation.spelling_evaluation,
            style_feedback=evaluation.style_evaluation,
            content_feedback=evaluation.content_evaluation,
            overall_feedback=evaluation.overall_evaluation,
            recommended_vocab=recommended_vocab
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

    mem_track.get_top_stats()
    return crud.get_generation(db, generation_id=generation.id)

@app.post("/round/{round_id}/end",tags=["Round"], response_model=schemas.RoundOut)
async def end_round(
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
async def read_vocabulary(current_user: Annotated[schemas.User, Depends(get_current_user)], vocabulary: str, pos: str=None, db: Session = Depends(get_db)):
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
async def read_vocabularies(current_user: Annotated[schemas.User, Depends(get_current_user)], skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view vocabularies")
    vocabularies = crud.get_vocabularies(db, skip=skip, limit=limit)
    return vocabularies

@app.post("/vocabularies", tags=["Vocabulary"], response_model=List[schemas.Vocabulary])
async def create_vocabularies(
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
        
        en_nlp = dictionary.Dictionary()

        for index, row in vocabularies.iterrows():
            pos = row['pos'].split(",")
            for p in pos:
                p = p.strip()

                meaning = await en_nlp.get_meaning(
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
async def read_personal_dictionaries(current_user: Annotated[schemas.User, Depends(get_current_user)], db: Session = Depends(get_db)):
    if not current_user:
        return []
    player_id = current_user.id
    personal_dictionaries = crud.get_personal_dictionaries(db, player_id=player_id)
    return personal_dictionaries

@app.post("/personal_dictionary/", tags=["Personal Dictionary"], response_model=schemas.PersonalDictionary)
async def create_personal_dictionary(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    personal_dictionary: schemas.PersonalDictionaryCreate,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to create personal dictionary")

    personal_dictionary.user_id = current_user.id

    en_nlp = dictionary.Dictionary()

    word_lemma = en_nlp.get_pos_lemma(
        word=personal_dictionary.vocabulary,
        relevant_sentence=personal_dictionary.relevant_sentence
    )
    
    vocab = crud.get_vocabulary(
        db=db,
        vocabulary=word_lemma['lemma'],
        part_of_speech=word_lemma['pos']
    )

    en_nlp = dictionary.Dictionary()

    if not vocab:
        meanings=await en_nlp.get_meaning(
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
async def update_personal_dictionary(
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
async def delete_personal_dictionary(
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
async def read_chat(
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
async def update_chat(
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
    
@app.get("/image_similarity/{generation_id}", tags=["Image"])
async def get_image_similarity(
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
    if db_generation:
        if db_generation.score_id:
            if db_generation.score.image_similarity:
                return db_generation.score.image_similarity
            return cal_image_similarity(
                generation=[{
                    'id': generation_id,
                }]
            )
    return None

@app.get("/generation/{generation_id}", tags=["Generation"], response_model=schemas.GenerationOut)
async def read_generation(
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
async def read_generations(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    player_id: Optional[int] = None,
    leaderboard_id: Optional[int] = None,
    program: Optional[str] = None,
    order_by: Optional[str] = "total_score",
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view generations")
    if player_id is not None and player_id != current_user.id and current_user.user_type == "student":
        raise HTTPException(status_code=401, detail="You are not authorized to view generations")

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

@app.get("/my_generations/", tags=["Generation"], response_model=list[Tuple[schemas.GenerationOut, schemas.RoundOut]])
async def read_my_generations(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    if not current_user:
        return []
    player_id = current_user.id
    generations = crud.get_generations(
        db=db,
        player_id=player_id,
        leaderboard_id=leaderboard_id,
    )
    return generations

@app.get("/generation/{generation_id}/score", tags=["Generation"], response_model=schemas.Score)
async def get_generation_score(
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
async def check_leaderboard_playable(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard_id: int, 
    program: Optional[str] = "none",
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to check leaderboard")
    
    if program != "none" or program != "overview":
        db_program = crud.get_program_by_name(db, program)
        if db_program:
            program_id = db_program.id
            db_rounds = crud.get_rounds(
                db=db,
                leaderboard_id=leaderboard_id,
                program_id=program_id
            )
            if db_rounds:
                return schemas.LeaderboardPlayable(
                    id=leaderboard_id,
                    is_playable=False
                )

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