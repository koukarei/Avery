from fastapi import Depends, FastAPI, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
import shutil, time, os
from pathlib import Path
from PIL import Image

from . import crud, models, schemas
from .database import SessionLocal, engine

from typing import Union, List, Annotated

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Define the directory where the images will be stored
media_dir = Path(os.getenv("MEDIA_DIR", "/media"))
media_dir.mkdir(parents=True, exist_ok=True)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)


@app.get("/users/", response_model=list[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.post("/users/{user_id}/rounds/", response_model=schemas.Round)
def create_round_for_user(
    user_id: int, leaderboard_id: Union[int,None], db: Session = Depends(get_db)
):
    return crud.create_round(db=db, leaderboard_id=leaderboard_id, user_id=user_id)

@app.get("/scenes/", response_model=list[schemas.Scene])
def read_scenes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    scenes = crud.get_scenes(db, skip=skip, limit=limit)
    return scenes

@app.post("/scene/", response_model=schemas.Scene)
def create_scene(scene: schemas.SceneBase, db: Session = Depends(get_db)):
    return crud.create_scene(db=db, scene=scene)

@app.get("/stories/", response_model=list[schemas.StoryOut])
def read_stories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    stories = crud.get_stories(db, skip=skip, limit=limit)
    return stories

@app.post("/story/", response_model=schemas.StoryOut)
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


@app.get("/leaderboards/", response_model=list[schemas.LeaderboardOut])
def read_leaderboards(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    leaderboards = crud.get_leaderboards(db, skip=skip, limit=limit)
    return leaderboards

@app.post("/leaderboards/", response_model=schemas.LeaderboardOut)
def create_leaderboard(
    original_image: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    story_extract: Annotated[str, Form()],
    scene_id: Annotated[int, Form()],
    story_id: Annotated[int, Form()],
    user_id: Annotated[int, Form()],
    db: Session = Depends(get_db),
):
    
    timestamp = str(int(time.time()))
    shortenfilename=".".join(original_image.filename.split(".")[:-1])[:20]
    fileattr = original_image.filename.split(".")[-1:][0]
    filename = f"o_{timestamp}_{shortenfilename}.{fileattr}"
    image_path = media_dir / "original_images" / filename

    try:
        Image.open(original_image.file)
    except Exception:
        raise HTTPException(status_code=400, detail="Please upload a valid image file")

    try:
        if not os.path.isfile(image_path):
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(original_image.file, buffer)
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

    db_leaderboard = schemas.LeaderboardCreate(
        title=title,
        story_extract=story_extract,
        scene_id=scene_id,
        story_id=story_id,
        original_image_id=db_original_image.id,
        created_by_id=user_id
    )
    
    return crud.create_leaderboard(
        db=db, 
        leaderboard=db_leaderboard,
    )

@app.get("/leaderboards/{leaderboard_id}", response_model=schemas.LeaderboardOut)
def read_leaderboard(leaderboard_id: int, db: Session = Depends(get_db)):
    db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
    if db_leaderboard is None:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    return db_leaderboard

@app.get("/leaderboards/{leaderboard_id}/rounds/", response_model=list[schemas.RoundOut])
def get_rounds_by_leaderboard(
    leaderboard_id: int,
    db: Session = Depends(get_db),
):
    return crud.get_rounds(
        db=db,
        leaderboard_id=leaderboard_id,
    )
