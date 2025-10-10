import logging.config
from fastapi import Depends, FastAPI, HTTPException, File, UploadFile, Form, responses, Security, status, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates
from fastapi import Request

templates = Jinja2Templates(directory="templates")

from fastapi.security import OAuth2PasswordRequestForm
from pydantic import parse_obj_as
from sqlalchemy.orm import Session
import time, os, datetime, shutil, tempfile, zipfile, zoneinfo, asyncio, json
import pandas as pd
from pathlib import Path

from . import crud, models, schemas, analysis_router
from tasks import app as celery_app
from tasks import generateDescription2, generate_interpretation2, calculate_score_gpt
from .database import SessionLocal2, engine2

from .dependencies import sentence, score, dictionary, openai_chatbot, lti
from .authentication import authenticate_user, authenticate_user_2, create_access_token, oauth2_scheme, SECRET_KEY, SECRET_KEY_WS, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, create_refresh_token, REFRESH_TOKEN_EXPIRE_MINUTES, JWTError, jwt, create_ws_token
from util import *

from typing import Tuple, List, Annotated, Optional, Union, Literal
from datetime import timezone, timedelta
from contextlib import asynccontextmanager
from celery import chain, group
import logging

from fastapi.middleware.cors import CORSMiddleware

from starlette.middleware.sessions import SessionMiddleware

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "ws://localhost:5173",
]

models.Base.metadata.create_all(bind=engine2)
# Define the directory where the images will be stored
media_dir = Path(os.getenv("MEDIA_DIR", "/static"))
media_dir.mkdir(parents=True, exist_ok=True)

# Dependency
def get_db():
    db = SessionLocal2()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(
    debug=True,
    title="AVERY",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=os.environ.get('SESSION_SECRET_KEY'))

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
        elif user.is_active:
            return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    else:
        raise credentials_exception

async def get_current_admin(db: Annotated[Session, Depends(get_db)],token: Annotated[schemas.TokenData, Depends(oauth2_scheme)]):
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
        elif user.is_admin:
            return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Only admin users are allowed",
            headers={"WWW-Authenticate": "Bearer"},
        )
    else:
        raise credentials_exception

app.include_router(
    analysis_router.router,
    dependencies=[Depends(get_current_admin)]
)

async def get_current_user_ws(db: Annotated[Session, Depends(get_db)],token: str):
#async def get_current_user(db: Annotated[Session, Depends(get_db)],username: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token:
    #if username:
        try:
            payload = jwt.decode(token, SECRET_KEY_WS, algorithms=[ALGORITHM])
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
        elif user.is_active:
            return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
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
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=user.id,
            action="login",
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    refresh_token = create_refresh_token(user.username)
    
    return schemas.Token(access_token=access_token,refresh_token=refresh_token, token_type="bearer")


@app.post("/lti/login")
async def lti_login(request: Request):
    valid = await lti.validate_lti_request(request)
    if not valid:
        return {'error': 'Invalid LTI request'} 
    
    # Extracting additional fields from the form data
    form_data = await request.form()

    user_id = form_data.get('user_id')
    oauth_consumer_key = form_data.get('oauth_consumer_key')

    if user_id:
        school = "School not provided"
        if oauth_consumer_key == "saikyo_consumer_key":
            school = "saikyo"
        elif oauth_consumer_key == "hikone_consumer_key":
            school = "hikone"
        elif oauth_consumer_key == "lms_consumer_key":
            school = "lms"
        elif oauth_consumer_key == "tom_consumer_key":
            school = "tom"
        elif oauth_consumer_key == "tomsec_consumer_key":
            school = "tomsec"
        elif oauth_consumer_key == "newleaf_consumer_key":
            school = "newleaf"

        if "instructor" in form_data.get('roles', '').lower():
            role = "instructor"
        else:
            role = "student"

        username = form_data.get('ext_user_username')
        user_login = schemas.UserLti(
            user_id=form_data.get('user_id'),
            username=username,
            display_name=form_data.get('lis_person_name_full', 'Unknown User'),
            roles=role,
            email=form_data.get('lis_person_contact_email_primary', ''),
            school=school,
        )
        
        user = authenticate_user_2(
            db=next(get_db()), 
            lti_user_id=user_login.user_id, 
            school=school
        )
        
        if user:
            try:
                token = await login_for_access_token_lti(user=user_login, db=next(get_db()))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to login: {str(e)}")
        else:
            # Create user
            response = await create_user_lti(user=user_login, db=next(get_db()))
            token = await login_for_access_token_lti(user=user_login, db=next(get_db()))


        return templates.TemplateResponse(
            "avery.html",
            {"request": request, "session_data": {
                "school": school,
                "access_token": token.access_token,
                "refresh_token": token.refresh_token,
                "token_type": token.token_type,
                "program": form_data.get('custom_program', 'none')
            }})
    raise HTTPException(status_code=500, detail="Failed to login")


@app.post("/lti/token",response_model=schemas.Token)
async def login_for_access_token_lti(
    user: schemas.UserLti,
    db: Session = Depends(get_db),
):
    
    user = authenticate_user_2(db, lti_user_id=user.user_id, school=user.school)
    
    if user == None or not user.lti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No LTI account found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=user.id,
            action="lti_login",
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    
    refresh_token = create_refresh_token(user.username)
    
    return schemas.Token(access_token=access_token,refresh_token=refresh_token, token_type="bearer")

@app.post("/refresh_token")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = crud.get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token}

@app.post("/ws_token", response_model=schemas.WSToken)
async def obtain_ws_token(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login to obtain WebSocket token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    ws_token = create_ws_token(
        data={"sub": current_user.username},
        expires_delta=timedelta(seconds=7200)  # 2 hours
    )
    return schemas.WSToken(ws_token=ws_token)

@app.post("/users/", tags=["User"], response_model=schemas.User, status_code=201)
async def create_user(user: Annotated[schemas.UserCreateIn, Form()], db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    user = schemas.UserCreate(
        **user.model_dump(exclude_none=True)
    )
    user.is_admin=False
    user.user_type="student"
    if user.username=="admin":
        user.is_admin=True
        user.user_type="instructor"
    new_user = crud.create_user(db=db, user=user)
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=new_user.id,
            action="create_user",
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return new_user

@app.post("/users/lti", tags=["User"], response_model=schemas.User)
async def create_user_lti(user: schemas.UserLti, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_lti(db, lti_user_id=user.user_id, school=user.school)
    if db_user:
        raise HTTPException(status_code=400, detail="This account already exists")
    new_user = crud.create_user_lti(db=db, user=user)
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=new_user.id,
            action="create_user_lti",
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return new_user

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

@app.put("/users/{user_id}/password", tags=["User"], response_model=schemas.User)
async def update_user_password(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    user: schemas.UserPasswordUpdate,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to update password")
    user_id = current_user.id
    return crud.update_user_password(db=db, user_id=user_id, new_password=user.new_password)

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

@app.get("/users/me", tags=["User"], response_model=schemas.User)
async def read_user_me(current_user: Annotated[schemas.User, Depends(get_current_user)], db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to read user")
    return current_user

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
    scenes = crud.get_scenes(db, skip=skip, limit=limit)
    return scenes

@app.post("/scene/", tags=["Scene"], response_model=schemas.Scene, status_code=201)
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
    stories = crud.get_stories(db, skip=skip, limit=limit)
    return stories
        

@app.post("/story/", tags=["Story"], response_model=schemas.StoryOut, status_code=201)
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
        story_content_file.file.seek(0)
        raw = story_content_file.file.read()
        if isinstance(raw, bytes):
            try:
                story_content = raw.decode('utf-8')
            except UnicodeDecodeError:
                # fallback for Windows-1252 / unknown encodings, preserve content
                story_content = raw.decode('cp1252', errors='replace')
        else:
            story_content = str(raw)

        storyCreate = schemas.StoryCreate(
            title=title,
            scene_id=scene_id,
            content=story_content
        )
                
    except Exception as e:
        logger1.error(f"Error uploading file: {str(e)}")
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
    
    # print("before convent",published_at_start, published_at_end)


    if published_at_start:
        published_at_start = datetime.datetime.strptime(published_at_start, "%d%m%Y").replace(tzinfo=zoneinfo.ZoneInfo('Japan'))
    if published_at_end:
        published_at_end = datetime.datetime.strptime(published_at_end, "%d%m%Y").replace(tzinfo=zoneinfo.ZoneInfo('Japan'))
    
    # print("after convert",published_at_start, published_at_end)

    if current_user.user_type == "student":
        if published_at_start and published_at_start > datetime.datetime.now(tz=zoneinfo.ZoneInfo('Japan')):
            published_at_start = datetime.datetime.now(tz=zoneinfo.ZoneInfo('Japan'))
        if published_at_end and published_at_end > datetime.datetime.now(tz=zoneinfo.ZoneInfo('Japan')):
            published_at_end = datetime.datetime.now(tz=zoneinfo.ZoneInfo('Japan'))
    
    # print("after check",published_at_start, published_at_end)

    leaderboards = crud.get_leaderboards(db, school_name=school_name, skip=skip, limit=limit, published_at_start=published_at_start, published_at_end=published_at_end)
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_leaderboards",
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )

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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_leaderboards_admin",
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )

    return leaderboards

@app.post("/leaderboards/", tags=["Leaderboard"], response_model=schemas.LeaderboardOut, status_code=201)
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
        created_by_id=current_user.id,
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

    t = generateDescription2.delay(
        leaderboard_id=result.id, 
        image=db_original_image.image, 
        story=story, 
        model_name="gpt-4o-mini"
    )
    if current_user.school:
        crud.add_leaderboard_school(db=db, leaderboard=schemas.LeaderboardUpdate(id=result.id, school=[current_user.school]))

    crud.create_task(
        db=db,
        task=schemas.Task(
            id=t.id,
            leaderboard_id=result.id,
        )
    )


    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="create_leaderboard",
            related_id=result.id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )

    return result

@app.post("/leaderboards/bulk_create", tags=["Leaderboard"], response_model=list[schemas.LeaderboardOut], status_code=201)
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
                        img = encode_image(image_file=f)
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
            logger1.error(f"Error creating images: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    # Read the CSV file
    try:
        
        leaderboards.set_index('title', inplace=True)

        # Create leaderboards
        leaderboard_list = []
        for index, row in leaderboards.iterrows():
            
            published_at = row.get('published_at', datetime.datetime.now(tz=timezone(timedelta(hours=9))))

            if 'story_extract' in leaderboards.columns:
                story_extract = row['story_extract']
            else:
                story_extract = ''

            if 'id' in leaderboards.columns:
                img_title = str(row['id']) + ' ' + index
            else:
                img_title = index
            img = images.get(remove_special_chars(img_title), None)

            if img is None:
                logger1.error(f"Image not found: {img_title}")
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

            # Add preset vocabularies
            if 'vocabularies' in leaderboards.columns:
                preset_vocabularies = row['vocabularies']
                preset_vocabularies = preset_vocabularies.split(",")
                preset_vocabularies = [word.strip() for word in preset_vocabularies]
                for word in preset_vocabularies:
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
                    logger1.info(f"Leaderboard {index} Added vocabularies: {diff}")
            
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
            t = generateDescription2.delay(
                leaderboard_id=db_leaderboard.id, 
                image=img.image, 
                story=story_extract, 
                model_name="gpt-4o-mini",
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

    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="create_leaderboards",
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )

    return leaderboard_list

@app.post("/leaderboards/image", tags=["Leaderboard"], response_model=schemas.IdOnly, status_code=201)
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
        img = encode_image(image_file=original_image.file)
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
        logger1.error(f"Leaderboard not found: {leaderboard_id}")
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_leaderboard_info",
            related_id=leaderboard_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )

    return db_leaderboard

@app.get("/leaderboards/{leaderboard_id}/schools/", tags=["Leaderboard"], response_model=list[schemas.SchoolOut])
async def read_schools(current_user: Annotated[schemas.User, Depends(get_current_user)], leaderboard_id: int, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view schools")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    schools = crud.get_school_leaderboard(db, leaderboard_id=leaderboard_id)
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_schools",
            related_id=leaderboard_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
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
    if not current_user.user_type == "instructor" or not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an instructor")
    db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
    if db_leaderboard is None:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="update_leaderboard_info",
            related_id=leaderboard_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return crud.update_leaderboard(db=db, leaderboard=leaderboard)

@app.put("/leaderboards/{leaderboard_id}/school", tags=["Leaderboard"], response_model=list[schemas.SchoolOut])
async def update_leaderboard_school(
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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="update_leaderboard_school",
            related_id=leaderboard_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return crud.add_leaderboard_school(db=db, leaderboard=schemas.LeaderboardUpdate(id=leaderboard_id, school=leaderboard.school))

@app.delete("/leaderboards/{leaderboard_id}/school", tags=["Leaderboard"], response_model=list[schemas.SchoolOut])
async def delete_leaderboard_school(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard_id: int,
    school: str,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to update leaderboard")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
    if db_leaderboard is None:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="delete_leaderboard_school",
            related_id=leaderboard_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return crud.remove_leaderboard_school(db=db, leaderboard=schemas.LeaderboardUpdate(id=leaderboard_id, school=[school]))

@app.put("/leaderboards/{leaderboard_id}/vocabulary", tags=["Leaderboard"], response_model=schemas.LeaderboardOut)
async def add_leaderboard_vocabulary(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard_id: int,
    vocabulary: schemas.VocabularyBase,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to update leaderboard")
    if not current_user.is_admin or not current_user.user_type == "instructor":
        raise HTTPException(status_code=401, detail="You are not an instructor")
    db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
    if db_leaderboard is None:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="add_leaderboard_vocabulary",
            related_id=leaderboard_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return crud.add_leaderboard_vocab(db=db, leaderboard_id=leaderboard_id, vocabulary=vocabulary)

@app.delete("/leaderboards/{leaderboard_id}/vocabulary", tags=["Leaderboard"], response_model=schemas.LeaderboardOut)
async def delete_leaderboard_vocabulary(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    leaderboard_id: int,
    vocabulary_id: int,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to update leaderboard")
    if not current_user.is_admin or not current_user.user_type == "instructor":
        raise HTTPException(status_code=401, detail="You are not an instructor")
    db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
    if db_leaderboard is None:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="delete_leaderboard_vocabulary",
            related_id=leaderboard_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return crud.remove_leaderboard_vocab(db=db, leaderboard_id=leaderboard_id, vocab_id=vocabulary_id)

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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="delete_leaderboard",
            related_id=leaderboard_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return crud.delete_leaderboard(db=db, leaderboard_id=leaderboard_id)

@app.post("/program", tags=["Program"], response_model=schemas.Program, status_code=201)
async def create_program(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    program: schemas.ProgramBase,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to create program")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="create_program",
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return crud.create_program(db=db, program=program)

@app.get("/programs/", tags=["Program"], response_model=list[schemas.Program])
async def read_programs(current_user: Annotated[schemas.User, Depends(get_current_user)], skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to read programs")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    programs = crud.get_programs(db, skip=skip, limit=limit)
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_programs",
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return programs

@app.get("/rounds/{round_id}", tags=["Round"], response_model=schemas.RoundOut)
async def get_round(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    round_id: int,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view")
    
    
    db_round = crud.get_round(db=db, round_id=round_id)
    if db_round is None:
        raise HTTPException(status_code=404, detail="Round not found")
    if db_round.player_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not allowed to view this round")
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_round",
            related_id=round_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )

    return db_round

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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_rounds_by_leaderboard",
            related_id=leaderboard_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )

    db_rounds = crud.get_rounds(
        db=db,
        leaderboard_id=leaderboard_id,
        program_id=db_program.id,
    )

    if current_user.user_type == "student":
        for r in db_rounds:
            r.player_id = None
    
    return db_rounds

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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_my_rounds",
            related_id=leaderboard_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )

    return crud.get_rounds(
        db=db,
        is_completed=is_completed,
        player_id=player_id,
        leaderboard_id=leaderboard_id,
    )

@app.websocket("/ws/{leaderboard_id}")
async def round_websocket(
    websocket: WebSocket,
    leaderboard_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    current_user = await get_current_user_ws(db=db, token=token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to connect")
    
    player_id = current_user.id

    # accept the websocket connection and record in database
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=player_id,
            action="connect websocket",
            sent_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
            received_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
        )
    )
    await websocket.accept()
    try:
        user_action = await websocket.receive_json()
        db_user_action = crud.create_user_action(
            db=db,
            user_action=schemas.UserActionBase(
                user_id=player_id,
                action=user_action["action"],
                received_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                sent_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
            )
        )
    except WebSocketDisconnect:
        # client disconnected immediately after connecting; record and exit gracefully
        crud.create_user_action(
            db=db,
            user_action=schemas.UserActionBase(
                user_id=player_id,
                action="disconnect websocket",
                sent_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                received_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
            )
        )
        logger1.info(f"WebSocket disconnected for user {player_id} before initial message")
        return
    except Exception as e:
        logger1.error(f"Error during websocket initial receive: {str(e)}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
        return

    # set program
    obj = parse_obj_as(schemas.RoundCreate, user_action['obj'])
    db_program = crud.get_program_by_name(db, obj.program)

    # if user resumes the round
    if user_action["action"] == "resume":
        leaderboard_id = user_action["obj"]["leaderboard_id"]
        
        unfinished_rounds = crud.get_rounds(
            db=db,
            player_id=player_id,
            leaderboard_id=leaderboard_id,
            is_completed=False,
            program_id=db_program.id
        )
        finished_rounds = crud.get_rounds(
            db=db,
            player_id=player_id,
            leaderboard_id=leaderboard_id,
            is_completed=True,
            program_id=db_program.id
        )

        if unfinished_rounds:
            db_round = crud.get_round(
                db=db,
                round_id=unfinished_rounds[0].id,
            )
            db_leaderboard = crud.get_leaderboard(db=db, leaderboard_id=leaderboard_id)
            
            db_generation = crud.get_generation(db=db, generation_id=db_round.last_generation_id)
            db_chat = crud.get_chat(db=db, chat_id=db_round.chat_history)
            prev_res_ids = [
                msg.response_id for msg in db_chat.messages if msg.response_id is not None
            ]
            chatbot_obj = openai_chatbot.Hint_Chatbot(
                model_name=db_round.model,
                vocabularies=db_leaderboard.vocabularies,
                first_res_id=db_leaderboard.response_id,
                prev_res_id=prev_res_ids[-1] if prev_res_ids else db_leaderboard.response_id,
                prev_res_ids=prev_res_ids
            )
            generated_time = db_generation.generated_time

            db_score = crud.get_score(db=db, generation_id=db_generation.id)

            # prepare data to send
            send_data = {
                "feedback": db_program.feedback,
                "leaderboard": {
                    "id": leaderboard_id,
                    "image": db_round.leaderboard.original_image.image,
                },
                "round": {
                    "id": db_round.id,
                    "generated_time":generated_time,
                    "generations": [
                        g.id for g in db_round.generations if g.is_completed
                    ]
                },
                "generation": {
                    "id": db_generation.id,
                    "interpreted_image": db_generation.interpreted_image.image if db_generation.interpreted_image else None,
                    "generated_time": db_generation.generated_time,
                    "sentence": db_generation.sentence,
                    "correct_sentence": db_generation.correct_sentence,
                    "is_completed": db_generation.is_completed,
                    "image_similarity": db_score.image_similarity if db_score else None,
                },
                "chat": {
                    "id": db_round.chat_history,
                    "messages" : [
                        {   
                            'id': db_message.id,
                            'sender': db_message.sender,
                            'content': db_message.content,
                            'created_at': db_message.created_at.isoformat(),
                            'is_hint': db_message.is_hint
                        }
                        for db_message in db_chat.messages
                    ]
                },
            }
        elif finished_rounds:
            db_round = crud.get_round(
                db=db,
                round_id=finished_rounds[0].id,
            )
            db_leaderboard = crud.get_leaderboard(db=db, leaderboard_id=leaderboard_id)
            
            db_generation = crud.get_generation(db=db, generation_id=db_round.last_generation_id)
            db_chat = crud.get_chat(db=db, chat_id=db_round.chat_history)
            prev_res_ids = [
                msg.response_id for msg in db_chat.messages if msg.response_id is not None
            ]
            chatbot_obj = openai_chatbot.Hint_Chatbot(
                model_name=db_round.model,
                vocabularies=db_leaderboard.vocabularies,
                first_res_id=db_leaderboard.response_id,
                prev_res_id=prev_res_ids[-1] if prev_res_ids else db_leaderboard.response_id,
                prev_res_ids=prev_res_ids
            )
            generated_time = db_generation.generated_time

            db_score = crud.get_score(db=db, generation_id=db_generation.id)

            # prepare data to send
            send_data = {
                "feedback": db_program.feedback,
                "leaderboard": {
                    "id": leaderboard_id,
                    "image": db_round.leaderboard.original_image.image,
                },
                "round": {
                    "id": db_round.id,
                    "generated_time":generated_time,
                    "generations": [
                        g.id for g in db_round.generations if g.is_completed
                    ]
                },
                "generation": {
                    "id": db_generation.id,
                    "interpreted_image": db_generation.interpreted_image.image if db_generation.interpreted_image else None,
                    "generated_time": db_generation.generated_time,
                    "sentence": db_generation.sentence,
                    "correct_sentence": db_generation.correct_sentence,
                    "is_completed": db_generation.is_completed,
                    "image_similarity": db_score.image_similarity if db_score else None,
                },
                "chat": {
                    "id": db_round.chat_history,
                    "messages" : [
                        {   
                            'id': db_message.id,
                            'sender': db_message.sender,
                            'content': db_message.content,
                            'created_at': db_message.created_at.isoformat(),
                            'is_hint': db_message.is_hint
                        }
                        for db_message in db_chat.messages
                    ]
                },
            }
        else:
            user_action["action"] = "start"

    if user_action["action"] == "start":

        db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
        db_score = None

        if db_program is None:
            db_round = crud.create_round(
                db=db,
                leaderboard_id=leaderboard_id,
                user_id=player_id,
                model_name=obj.model,
                created_at=obj.created_at,
            )

        else:
            db_round = crud.create_round(
                db=db,
                leaderboard_id=leaderboard_id,
                user_id=player_id,
                program_id=db_program.id,
                model_name=obj.model,
                created_at=obj.created_at,
            )

        db_generation = crud.create_generation(
            db=db,
            round_id=db_round.id,
            generation=schemas.GenerationCreate(
                round_id=db_round.id,
                sentence='',
                generated_time=0,
                created_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
            )
        )

        db_message = crud.create_message(
            db=db,
            message=schemas.MessageBase(
                content="画像を説明する際にヒントが使えます。下の『Averyへのメッセージ🤖』に質問したい内容を入力してくださいね！",
                sender="assistant",
                created_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                is_hint=False
            ),
            chat_id=db_round.chat_history
        )['message']

        chatbot_obj = openai_chatbot.Hint_Chatbot(
            model_name=obj.model,
            vocabularies=db_leaderboard.vocabularies,
            first_res_id=db_leaderboard.response_id,
            prev_res_id=db_leaderboard.response_id
        )

        generated_time = 0

        # prepare data to send
        send_data = {
            "feedback": db_program.feedback,
            "leaderboard": {
                "id": leaderboard_id,
                "image": db_round.leaderboard.original_image.image,
            },
            "round": {
                "id": db_round.id,
                "generated_time":generated_time,
                "generations": []
            },
            "generation": {
                "id": db_generation.id,
                "interpreted_image": db_generation.interpreted_image.image if db_generation.interpreted_image else None,
                "generated_time": db_generation.generated_time,
                "correct_sentence": db_generation.correct_sentence,
                "is_completed": db_generation.is_completed,
                "image_similarity": db_score.image_similarity if db_score else None,
            },
            "chat": {
                "id": db_round.chat_history,
                "messages" : [
                    {   
                        'id': db_message.id,
                        'sender': db_message.sender,
                        'content': db_message.content,
                        'created_at': db_message.created_at.isoformat(),
                        'is_hint': db_message.is_hint
                    }
                ]
            },
        }
    
    await websocket.send_json(send_data)

    crud.update_user_action(
        db=db,
        user_action=schemas.UserActionUpdate(
            id=db_user_action.id,
            related_id=db_generation.id if db_generation else None,
            sent_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
        )
    )

    try:
        while True:
            user_action = await websocket.receive_json()

            db_user_action = crud.create_user_action(
                db=db,
                user_action=schemas.UserActionBase(
                    user_id=player_id,
                    action=user_action["action"],
                    related_id=db_generation.id if db_generation else None,
                    received_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                    sent_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                )
            )

            # if user asks for a hint
            if user_action["action"] == "hint":
                db_messages = []
                obj = parse_obj_as(schemas.MessageReceive, user_action['obj'])
                crud.create_message(
                    db=db,
                    message=schemas.MessageBase(
                        content=obj.content,
                        sender="user",
                        created_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                        is_hint=True
                    ),
                    chat_id=db_round.chat_history
                )

                hint = chatbot_obj.nextResponse(
                    ask_for_hint=obj.content,
                    new_messages=[],
                    base64_image=db_round.leaderboard.original_image.image,
                )

                db_messages.append(
                    crud.create_message(
                        db=db,
                        message=schemas.MessageBase(
                            content=hint,
                            sender="assistant",
                            created_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                            is_hint=True,
                            response_id=chatbot_obj.prev_res_id
                        ),
                        chat_id=db_round.chat_history
                    )['message']
                )

                send_data = {
                    "chat": {
                        "id": db_round.chat_history,
                        "messages" : [
                            {   
                                'id': db_message.id,
                                'sender': db_message.sender,
                                'content': db_message.content,
                                'created_at': db_message.created_at.isoformat(),
                                'is_hint': db_message.is_hint
                            }
                            for db_message in db_messages
                        ]
                    },
                }

            # if user submits the answer
            elif user_action["action"] == "submit":
                obj = parse_obj_as(schemas.GenerationCreate, user_action['obj'])
                status = 0
                sentences = [
                    g.sentence.strip() for g in db_round.generations if g.sentence != '' and g.correct_sentence is not None and g.id != db_generation.id
                ]
                
                if db_generation.correct_sentence is None:
                    db_generation = crud.update_generation0(
                        db=db,
                        generation=obj,
                        generation_id=db_generation.id
                    )
                elif obj.sentence.strip() in sentences:
                    db_generation = crud.get_generation(db=db, generation_id=db_generation.id)
                    status = 3
                else: 
                    generated_time = generated_time + 1 
                    obj.generated_time = generated_time
                    db_generation = crud.create_generation(
                        db=db,
                        round_id=db_round.id,
                        generation=obj,
                    )

                if status != 3:
                    try:
                        status, correct_sentence, spelling_mistakes, grammar_mistakes=sentence.checkSentence(passage=db_generation.sentence)
                    except Exception as e:
                        logger1.error(f"Error in get_user_answer: {str(e)}")
                        raise HTTPException(status_code=400, detail=str(e))
                

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
                    
                    db_generation = crud.update_generation1(
                        db=db,
                        generation=schemas.GenerationCorrectSentence(
                            id=db_generation.id,
                            correct_sentence=correct_sentence
                        )
                    )

                    messages = [
                        schemas.MessageBase(
                            content="""回答を記録しました。📝
あなたの回答（画像生成に参考された）: {}\n\n修正された回答：{}""".format(db_generation.sentence, db_generation.correct_sentence),
                            sender="assistant",
                            created_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                            is_hint=False
                        )
                    ]

                    # server-side processing
                    generation_dict = {
                        "id": db_generation.id,
                        "at": db_generation.created_at,
                    }
    
                    if "IMG" in db_program.feedback and "AWS" in db_program.feedback:
                        chain_interpretation = chain(
                            group(
                                generate_interpretation2.s(generation_id=db_generation.id, sentence=db_generation.sentence, at=db_generation.created_at),
                            ),
                            group(
                                calculate_score_gpt.s(),
                            ),
                        )
                        chain_result = chain_interpretation.apply_async()
                    # elif "IMG" in db_program.feedback:
                    #     chain_interpretation = chain(
                    #         group(
                    #             generate_interpretation2.s(generation_id=db_generation.id, sentence=db_generation.sentence, at=db_generation.created_at),
                    #         )
                    #     )
                    #     chain_result = chain_interpretation.apply_async()
                    elif "AWS" in db_program.feedback:
                        chain_interpretation = chain(
                            group(
                                calculate_score_gpt.s(items=generation_dict),
                            ),
                        )
                        chain_result = chain_interpretation.apply_async()
                    else:
                        chain_result = None
                    

                elif status == 1:
                    messages = [
                        schemas.MessageBase(
                            content="ブー！英語で答えてください。",
                            sender="assistant",
                            created_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                            is_hint=False
                        )
                    ]

                elif status == 2:
                    messages = [
                        schemas.MessageBase(
                            content="ブー！不適切な言葉が含まれています。",
                            sender="assistant",
                            created_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                            is_hint=False
                        )
                    ]

                elif status == 3:
                    messages = [
                        schemas.MessageBase(
                            content="ブー！同じ回答がすでに提出されています。新しいアイデアを試してみましょう！",
                            sender="assistant",
                            created_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                            is_hint=False
                        )
                    ]
                else:
                    messages = []

                db_messages = []

                for message in messages:
                    db_messages.append(
                        crud.create_message(
                            db=db,
                            message=message,
                            chat_id=db_round.chat_history
                        )['message']
                    )

                # prepare data to send
                send_data = {
                    "leaderboard": {
                        "id": leaderboard_id,
                        "image": db_round.leaderboard.original_image.image,
                    },
                    "round": {
                        "id": db_round.id,
                        "generated_time":generated_time,
                    },
                    "chat": {
                        "id": db_round.chat_history,
                        "messages" : [
                            {   
                                'id': db_message.id,
                                'sender': db_message.sender,
                                'content': db_message.content,
                                'created_at': db_message.created_at.isoformat(),
                                'is_hint': db_message.is_hint
                            }
                            for db_message in db_messages
                        ]
                    },
                    "generation": {
                        "id": db_generation.id,
                        "correct_sentence": db_generation.correct_sentence if status == 0 else None,
                    }
                }

                # if "IMG" in db_program.feedback or "AWS" in db_program.feedback:
                #     while True:
                #         db_generation = crud.get_generation(
                #             db=db,
                #             generation_id=db_generation.id
                #         )
                #         if db_generation.is_completed:
                #             break
                #         elif chain_result.failed():
                #             raise HTTPException(status_code=500, detail="Error in chain result")
                #         elif chain_result.successful():
                #             break
                #         elif ("AWS" in db_program.feedback and db_generation.score is not None) and ("IMG" in db_program.feedback and db_generation.interpreted_image is not None):
                #             break
                #         elif ("AWS" in db_program.feedback and db_generation.score is not None) and ("IMG" not in db_program.feedback):
                #             break
                #         elif ("AWS" not in db_program.feedback) and ("IMG" in db_program.feedback and db_generation.interpreted_image is not None):
                #             break
                        
                #         logger1.info(f"Waiting for the task to finish... {chain_result.status}")
                #         await websocket.send_json({"feedback": "waiting"})
                #         await asyncio.sleep(3)

            elif user_action["action"] == "evaluate" and (db_generation.correct_sentence is None or db_generation.correct_sentence == ""):
                send_data = {}
            elif user_action["action"] == "evaluate":
                
                if "IMG" in db_program.feedback and db_generation.interpreted_image is None:
                    # If the interpreted image is not generated, log an error
                    #logger1.error(f"Interpreted image not found for generation {db_generation.id}")
                    generate_interpretation2(generation_id=db_generation.id, sentence=db_generation.sentence, at=db_generation.created_at)

                if "AWS" in db_program.feedback:
                    db_score = db_generation.score
                    if db_score is not None:
                        image_similarity = db_score.image_similarity
                        scores_dict = {
                            'grammar_score': db_score.grammar_score,
                            'spelling_score': db_score.spelling_score,
                            'vividness_score': db_score.vividness_score,
                            'convention': db_score.convention,
                            'structure_score': db_score.structure_score,
                            'content_score': db_score.content_score,
                            'total_score': db_generation.total_score,
                        }
                    elif locals().get('chain_result'):
                        # Get the result from the chain
                        chain_score_result = [
                            json.loads(result) for result in chain_result.result
                        ]
                        scores_dict = {
                            'grammar_score': chain_score_result[1].get('grammar_score', 0),
                            'spelling_score': chain_score_result[1].get('spelling_score', 0),
                            'vividness_score': chain_score_result[1].get('vividness_score', 0),
                            'convention': chain_score_result[1].get('convention', 0),
                            'structure_score': chain_score_result[1].get('structure_score', 0),
                            'content_score': chain_score_result[1].get('content_score', 0),
                            'total_score': chain_score_result[0].get('total_score', 0),
                        }
                        image_similarity = chain_score_result[1].get('image_similarity', 0)
                    else:
                        raise HTTPException(status_code=500, detail="No score found")
                else:
                    scores_dict = None
                    image_similarity = None
                
                if not db_generation.is_completed:
                    generation_aware = db_generation.created_at.replace(tzinfo=timezone(timedelta(hours=9)))
                    db_generation_aware = db_round.created_at.replace(tzinfo=timezone(timedelta(hours=9)))
                    duration = (generation_aware - db_generation_aware).seconds
                    
                    generation_com = schemas.GenerationComplete(
                        id=db_generation.id,
                        duration=duration,
                        is_completed=True
                    )
                    crud.update_generation3(
                        db=db,
                        generation=generation_com
                    )

                    descriptions = crud.get_description(db, leaderboard_id=db_round.leaderboard_id, model_name=db_round.model)
                    descriptions = [des.content for des in descriptions]
    
                    # Set messages for score and evaluation
                    db_messages = []

                    if "AWS" in db_program.feedback:
                        score_message = """あなたの回答（評価対象）：{user_sentence}

修正された回答　　　　 ：{correct_sentence}


| 　　          | 得点   | 満点       |
|---------------|--------|------|
| 文法得点      |{:>5}|  3  |
| スペリング得点|{:>5}|  1  |
| 鮮明さ        |{:>5}|  1  |
| 自然さ        |{:>5}|  1  |
| 構造性        |{:>5}|  1  |
| 内容得点      |{:>5}|  3  |
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

                        db_messages.append(crud.create_message(
                            db=db,
                            message=schemas.MessageBase(
                                content=score_message,
                                sender="assistant",
                                created_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                                is_hint=False,
                                is_evaluation=True,
                            ),
                            chat_id=db_round.chat_history
                        )['message'])

                    if "AWE" in db_program.feedback:
                        evaluation = chatbot_obj.get_result(
                            sentence=db_generation.sentence,
                            correct_sentence=db_generation.correct_sentence,
                            base64_image=db_round.leaderboard.original_image.image,
                            grammar_errors=db_generation.grammar_errors,
                            spelling_errors=db_generation.spelling_errors,
                            descriptions=descriptions
                        )
                    else:
                        evaluation = None
                        db_evaluate_msg = None


                    if evaluation:
                        recommended_vocab = ""
                        if len(db_round.generations) > 2:
                            recommended_vocabs = db_round.leaderboard.vocabularies
                            recommended_vocabs = [vocab.word for vocab in recommended_vocabs]
                            if recommended_vocabs:
                                recommended_vocab = "\n\n**おすすめの単語**\n" + ", ".join(recommended_vocabs)

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
                            grammar_feedback=evaluation['grammar_evaluation'],
                            spelling_feedback=evaluation['spelling_evaluation'],
                            style_feedback=evaluation['style_evaluation'],
                            content_feedback=evaluation['content_evaluation'],
                            overall_feedback=evaluation['overall_evaluation'],
                            recommended_vocab=recommended_vocab
                        )

                        db_evaluate_msg = crud.create_message(
                            db=db,
                            message=schemas.MessageBase(
                                content=evaluation_message,
                                sender="assistant",
                                created_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
                                is_hint=False,
                               
                                is_evaluation=True,
                                responses_id=chatbot_obj.prev_res_id
                            ),
                            chat_id=db_round.chat_history
                        )['message']

                        db_messages.append(db_evaluate_msg)

                    generation_com = schemas.GenerationComplete(
                        id=db_generation.id,
                        is_completed=True,
                        duration=duration,
                        evaluation_id=db_evaluate_msg.id if db_evaluate_msg else None
                    )

                    db_generation = crud.update_generation3(
                        db=db,
                        generation=generation_com,
                    )

                # prepare data to send
                send_data = {
                    "leaderboard": {
                        "id": leaderboard_id,
                        "image": db_leaderboard.original_image.image,
                    },
                    "round": {
                        "id": db_round.id,
                        "generated_time":generated_time,
                    },
                    "chat": {
                        "id": db_round.chat_history,
                        "messages" : [
                            {   
                                'id': db_message.id,
                                'sender': db_message.sender,
                                'content': db_message.content,
                                'created_at': db_message.created_at.isoformat(),
                                'is_hint': db_message.is_hint
                            }
                            for db_message in db_messages
                        ]
                    },
                    "generation": {
                        "id": db_generation.id,
                        "interpreted_image": db_generation.interpreted_image.image if db_generation.interpreted_image else None,
                        "image_similarity": image_similarity,
                        "evaluation_msg": db_evaluate_msg.content if 'AWE' in db_program.feedback else None
                    }
                }

            # if user requests to end the round
            elif user_action["action"] == "end":
                now_tim = datetime.datetime.now(tz=timezone(timedelta(hours=9)))
                start_round = db_round.created_at.replace(tzinfo=timezone(timedelta(hours=9)))
                duration = (now_tim - start_round).seconds

                db_round = crud.complete_round(
                    db=db,
                    round_id=db_round.id,
                    round=schemas.RoundComplete(
                        id=db_round.id,
                        last_generation_id=db_generation.id,
                        is_completed=True,
                        duration=duration,
                    )
                )
                
                # prepare data to send
                send_data = {
                    "leaderboard": {
                        "id": leaderboard_id,
                        "image": db_leaderboard.original_image.image,
                    },
                    "round": {
                        "id": db_round.id,
                        "generated_time":generated_time,
                    },
                    "chat": {
                        "id": db_round.chat_history,
                        "messages" : []
                    },
                }

                chatbot_obj.kill()

            # send details to the user
            await websocket.send_json(send_data)

            crud.update_user_action(
                db=db,
                user_action=schemas.UserActionUpdate(
                    id=db_user_action.id,
                    related_id=db_generation.id if db_generation else None,
                    sent_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                )
            )

    except WebSocketDisconnect:
        # record disconnect time
        crud.create_user_action(
            db=db,
            user_action=schemas.UserActionBase(
                user_id=player_id,
                action="disconnect websocket",
                sent_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
                received_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
            )
        )
        logger1.info(f"WebSocket disconnected for user {player_id}")
    except Exception as e:
        logger1.error(f"Error in websocket: {str(e)}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass

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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="check_vocabulary_info",
            related_id=vocabularies[0].id if vocabularies else None,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return vocabularies

@app.get("/vocabularies/", tags=["Vocabulary"], response_model=list[schemas.Vocabulary])
async def read_vocabularies(current_user: Annotated[schemas.User, Depends(get_current_user)], skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view vocabularies")
    vocabularies = crud.get_vocabularies(db, skip=skip, limit=limit)
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="check_vocabularies",
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return vocabularies

@app.post("/vocabularies", tags=["Vocabulary"], response_model=List[schemas.Vocabulary], status_code=201)
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
        
        for index, row in vocabularies.iterrows():
            pos = row['pos'].split(",")
            for p in pos:
                p = p.strip()

                meaning = await dictionary.get_meaning(
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
    
        crud.create_user_action(
            db=db,
            user_action=schemas.UserActionBase(
                user_id=current_user.id,
                action="create_vocabularies",
                sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
                received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            )
        )
        return output
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/personal_dictionaries/", tags=["Personal Dictionary"], response_model=list[schemas.PersonalDictionary])
async def read_personal_dictionaries(current_user: Annotated[schemas.User, Depends(get_current_user)], db: Session = Depends(get_db)):
    if not current_user:
        return []
    player_id = current_user.id
    personal_dictionaries = crud.get_personal_dictionaries(db, player_id=player_id)
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_personal_dictionary",
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return personal_dictionaries

@app.post("/personal_dictionary/", tags=["Personal Dictionary"], response_model=schemas.PersonalDictionary, status_code=201)
async def create_personal_dictionary(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    personal_dictionary: schemas.PersonalDictionaryCreate,
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to create personal dictionary")

    personal_dictionary.user_id = current_user.id
    
    vocab = crud.get_vocabulary(
        db=db,
        vocabulary=personal_dictionary.vocabulary,
        part_of_speech=personal_dictionary.pos
    )


    if not vocab:
        meanings=await dictionary.get_meaning(
            lemma=personal_dictionary.vocabulary,
            pos=personal_dictionary.pos
        )
        if isinstance(meanings, list):
            meaning = '; '.join(meanings)
        else:
            meaning = meanings

        vocab = crud.create_vocabulary(
            db=db,
            vocabulary=schemas.VocabularyBase(
                word=personal_dictionary.vocabulary,
                pos=personal_dictionary.pos,
                meaning=meaning
            )
        )
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="create_personal_dictionary",
            related_id=vocab.id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="update_personal_dictionary",
            related_id=personal_dictionary.id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="delete_personal_dictionary",
            related_id=personal_dictionary_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return crud.delete_personal_dictionary(
        db=db,
        player_id=current_user.id,
        vocabulary_id=personal_dictionary_id,
    )
@app.get("/evaluation_msg/{generation_id}", tags=["Generation"], response_model=schemas.Message)
async def get_evaluation(
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

    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_evaluation",
            related_id=generation_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    if "AWE" in db_round.program.feedback and db_generation.is_completed:
        if db_generation.evaluation is None:
            # Generate evaluation if generation is completed but no evaluation exists
            db_chat = crud.get_chat(
                db=db,
                chat_id=db_round.chat_history
            )
            prev_res_ids = [
                msg.response_id for msg in db_chat.messages if msg.response_id is not None
            ]
            
            chatbot_obj = openai_chatbot.Hint_Chatbot(
                model_name=db_round.model,
                vocabularies=db_round.leaderboard.vocabularies,
                first_res_id=db_round.leaderboard.response_id,
                prev_res_id=prev_res_ids[-1] if prev_res_ids else db_round.leaderboard.response_id,
                prev_res_ids=prev_res_ids
            )

            descriptions = crud.get_description(db, leaderboard_id=db_round.leaderboard_id, model_name=db_round.model)
            evaluation = chatbot_obj.get_result(
                sentence=db_generation.sentence,
                correct_sentence=db_generation.correct_sentence,
                base64_image=db_round.leaderboard.original_image.image,
                grammar_errors=db_generation.grammar_errors,
                spelling_errors=db_generation.spelling_errors,
                descriptions=[des.content for des in descriptions]
            )

            if evaluation:
                recommended_vocab = ""
                if len(db_round.generations) > 2:
                    recommended_vocabs = db_round.leaderboard.vocabularies
                    recommended_vocabs = [vocab.word for vocab in recommended_vocabs]
                    if recommended_vocabs:
                        recommended_vocab = "\n\n**おすすめの単語**\n" + ", ".join(recommended_vocabs)

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
                    grammar_feedback=evaluation['grammar_evaluation'],
                    spelling_feedback=evaluation['spelling_evaluation'],
                    style_feedback=evaluation['style_evaluation'],
                    content_feedback=evaluation['content_evaluation'],
                    overall_feedback=evaluation['overall_evaluation'],
                    recommended_vocab=recommended_vocab
                )

                db_evaluate_msg = crud.create_message(
                    db=db,
                    message=schemas.MessageBase(
                        content=evaluation_message,
                        sender="assistant",
                        created_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
                        is_hint=False,
                        is_evaluation=True,
                        responses_id=chatbot_obj.prev_res_id
                    ),
                    chat_id=db_round.chat_history
                )['message']
                
                db_generation = crud.update_generation3(
                    db=db,
                    generation=schemas.GenerationComplete(
                        id=db_generation.id,
                        is_completed=True,
                        evaluation_id=db_evaluate_msg.id if db_evaluate_msg else None
                    )
                )
        return db_generation.evaluation
    
    raise HTTPException(status_code=500, detail="No evaluation message.")

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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_chat",
            related_id=round_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return chat


@app.get("/chat/{round_id}/stats", tags=["Chat"], response_model=schemas.ChatStats)
async def read_chat_stats(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    round_id: int, 
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view chat stats")
    db_round = crud.get_round(db, round_id)
    if db_round is None:
        raise HTTPException(status_code=404, detail="Round not found")
    
    chat_id = db_round.chat_history
    chat_stats = crud.get_chat_stats(db, chat_id=chat_id)
    if chat_stats is None:
        raise HTTPException(status_code=404, detail="Chat stats not found")
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_chat_stats",
            related_id=round_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return chat_stats

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
    
    imgdata = decode_image(db_leaderboard.original_image.image)
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_original_image",
            related_id=leaderboard_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return responses.Response(
        content=imgdata,
        media_type="image/png"  # Adjust this based on your image type (jpeg, png, etc.)
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
    
    imgdata = decode_image(db_generation.interpreted_image.image)
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_interpreted_image",
            related_id=generation_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    return responses.Response(
        content=imgdata,
        media_type="image/jpeg"  # Adjust this based on your image type (jpeg, png, etc.)
    )

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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_generation_info",
            related_id=generation_id,
            sent_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
            received_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
        )
    )

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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_generations",
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )

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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_my_generations",
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )
    player_id = current_user.id
    generations = crud.get_generations(
        db=db,
        player_id=player_id,
        leaderboard_id=leaderboard_id,
    )

    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view my generations",
            sent_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
            received_at=datetime.datetime.now(tz=timezone(timedelta(hours=9))),
        )
    )
    return generations

@app.get("/generation/{generation_id}/score", tags=["Generation"], response_model=Optional[schemas.Score])
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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="view_generation_score",
            related_id=generation_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )

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
    
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=current_user.id,
            action="check_leaderboard_playable",
            related_id=leaderboard_id,
            sent_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            received_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
    )

    if program != "none" and program != "overview":
        db_program = crud.get_program_by_name(db, program)
        if db_program:
            program_id = db_program.id
            db_rounds = crud.get_rounds(
                db=db,
                leaderboard_id=leaderboard_id,
                program_id=program_id,
                player_id=current_user.id
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

@app.get("/generations/fix_error", tags=["Task"], response_model=list[Union[schemas.GenerationOut, schemas.Score, schemas.InterpretedImage]])
async def read_error(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    group_type: Literal["no_image", "no_interpretation", "no_score", "no_content_score","no_word_num","no_grammar","no_perplexity","no_similarity","no_complete"],
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to view error")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    return crud.get_error_task(db, group_type=str(group_type))

@app.post("/tasks/fix_error", tags=["Task"])
async def fix_error_task(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to fix error")
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="You are not an admin")
    
    try:

        db_images = crud.get_error_task(
            db=db,
            group_type='no_interpretation'
        )

        if db_images:
            for db_image in db_images:
                crud.delete_interpreted_image(
                    db=db,
                    image_id=db_image.id
                )

        chain_interpretations = []
        # stop at generating images
        db_generations = crud.get_error_task(
            db=db,
            group_type='no_complete'
        )
        if db_generations:
            for db_generation in db_generations:
                generation_dict = {
                    "id": db_generation.id,
                    "at": db_generation.created_at,
                }
                chain_interpretation = chain(
                    group(
                        generate_interpretation2.s(generation_id=db_generation.id, sentence=db_generation.sentence, at=db_generation.created_at),
                    ),
                    group(
                        calculate_score_gpt.s()
                    ),
                )
                chain_interpretation.apply_async()
                chain_interpretations.append(chain_interpretation)

        db_generations = crud.get_error_task(
            db=db,
            group_type='no_score'
        )

        if db_generations:
            for db_generation in db_generations:
                generation_dict = {
                    "id": db_generation.id,
                    "at": db_generation.created_at,
                }
                calculate_score_gpt.s(
                    items=[generation_dict],
                )

        return chain_interpretations
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))