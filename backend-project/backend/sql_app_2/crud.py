from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from . import models, schemas

from typing import List, Optional, Literal, Union
import datetime

from .authentication import get_password_hash

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_lti(db: Session, lti_user_id: int, school: str):
    return db.query(models.User).filter(models.User.lti_user_id == lti_user_id).filter(models.User.school == school).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)

    db_userprofile = models.UserProfile(
        display_name=user.display_name,
        bio="",
        avatar="",
        level=1,
        xp=0
    )

    db.add(db_userprofile)
    db.commit()
    db.refresh(db_userprofile)

    db_user = models.User(
        email=user.email,
        username=user.username, 
        hashed_password=hashed_password,
        is_active=True,
        profile_id=db_userprofile.id,
        is_admin=user.is_admin,
        user_type=user.user_type
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

def create_user_lti(db: Session, user: schemas.UserLti):
    random_password = str(datetime.datetime.now())
    hashed_password = get_password_hash(random_password)
    db_userprofile = models.UserProfile(
        display_name=user.display_name,
        bio="",
        avatar="",
        level=1,
        xp=0
    )

    db.add(db_userprofile)
    db.commit()
    db.refresh(db_userprofile)

    internal_username = f"{user.user_id}_{user.school}"

    db_user = models.User(
        lti=True,
        lti_user_id=user.user_id,
        lti_username=user.username,
        school=user.school,
        email=user.email,
        username=internal_username, 
        hashed_password=hashed_password,
        is_active=True,
        profile_id=db_userprofile.id,
        is_admin=False,
        user_type=user.roles
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

def update_user(db: Session, user: schemas.UserUpdate):
    db.bulk_update_mappings(models.User, [user.model_dump()])
    db.commit()
    db_user = db.query(models.User).filter(models.User.id == user.id).first()
    return db_user

def update_user_password(db: Session, user_id: int, new_password: str):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    db_user.hashed_password = get_password_hash(new_password)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    db_user_profile = db.query(models.UserProfile).filter(models.UserProfile.id == db_user.profile_id).first()
    if db_user_profile:
        db.delete(db_user_profile)
        db.commit()
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user

def get_leaderboards(
        db: Session, 
        school_name: str = None,
        skip: int = 0, 
        limit: int = 100, 
        published_at_start: datetime.datetime = None,
        published_at_end: datetime.datetime = None,
        is_public: bool = True
):
    if school_name:
        school_leaderboards = db.query(
            models.Leaderboard,
            models.School_Leaderboard
        ).\
        filter(models.School_Leaderboard.school == school_name).\
        join(
            models.Leaderboard,
            models.Leaderboard.id == models.School_Leaderboard.leaderboard_id
        )
    else:
        school_leaderboards = db.query(
            models.Leaderboard,
            models.School_Leaderboard
        ).join(
            models.Leaderboard,
            models.Leaderboard.id == models.School_Leaderboard.leaderboard_id
        )

    if published_at_start is None and published_at_end is None:
        return school_leaderboards.\
            filter(models.Leaderboard.is_public == is_public).\
            filter(models.Leaderboard.published_at <= datetime.datetime.now()).\
                offset(skip).limit(limit).all()
    elif published_at_start is None:
        return school_leaderboards.\
            filter(models.Leaderboard.is_public == is_public).\
            filter(models.Leaderboard.published_at <= published_at_end).\
                offset(skip).limit(limit).all()
    elif published_at_end is None:
        published_at_end = datetime.datetime.now()
    return school_leaderboards.\
        filter(models.Leaderboard.is_public == is_public).\
        filter(models.Leaderboard.published_at >= published_at_start).\
        filter(models.Leaderboard.published_at <= published_at_end).\
                offset(skip).limit(limit).all()

def get_leaderboards_admin(
        db: Session, 
        skip: int = 0, 
        limit: int = 100, 
        published_at_start: datetime.datetime = None,
        published_at_end: datetime.datetime = None,
):
    if published_at_start is None and published_at_end is None:
        return db.query(models.Leaderboard).\
            filter(models.Leaderboard.published_at <= datetime.datetime.now()).\
                offset(skip).limit(limit).all()
    elif published_at_start is None:
        return db.query(models.Leaderboard).\
            filter(models.Leaderboard.published_at <= published_at_end).\
                offset(skip).limit(limit).all()
    elif published_at_end is None:
        published_at_end = datetime.datetime.now()
    return db.query(models.Leaderboard).\
        filter(models.Leaderboard.published_at >= published_at_start).\
            filter(models.Leaderboard.published_at <= published_at_end).\
                offset(skip).limit(limit).all()

def get_leaderboard(db: Session, leaderboard_id: int):
    return db.query(models.Leaderboard).filter(models.Leaderboard.id == leaderboard_id).first()

def get_school_leaderboard(db: Session, leaderboard_id: int):
    return db.query(models.School_Leaderboard).filter(models.School_Leaderboard.leaderboard_id == leaderboard_id).all()

def create_leaderboard(
        db: Session, 
        leaderboard: schemas.LeaderboardCreate,
):
    db_leaderboard = models.Leaderboard(
        **leaderboard.model_dump()
    )

    db.add(db_leaderboard)
    db.commit()
    db.refresh(db_leaderboard)
    return db_leaderboard

def update_leaderboard(
        db: Session,
        leaderboard: Union[schemas.LeaderboardUpdate , schemas.LeaderboardUpdateInternal]
):
    db_leaderboard = db.query(models.Leaderboard).filter(models.Leaderboard.id == leaderboard.id).first()
    if db_leaderboard is None:
        raise ValueError("Leaderboard not found")
    if leaderboard.is_public is not None:
        db_leaderboard.is_public = leaderboard.is_public
    if leaderboard.published_at is not None:
        db_leaderboard.published_at = leaderboard.published_at
    if leaderboard.title is not None:
        db_leaderboard.title = leaderboard.title
    if leaderboard.story_extract is not None:
        db_leaderboard.story_extract = leaderboard.story_extract
    if leaderboard.scene_id is not None:
        db_leaderboard.scene_id = leaderboard.scene_id
    if leaderboard.story_id is not None:
        db_leaderboard.story_id = leaderboard.story_id
        
    db.commit()
    db.refresh(db_leaderboard)

    if type(leaderboard) is schemas.LeaderboardUpdateInternal and leaderboard.response_id is not None:
        db_leaderboard.response_id = leaderboard.response_id
        db.commit()
        db.refresh(db_leaderboard)
    
    return db_leaderboard

def add_leaderboard_school(
        db: Session,
        leaderboard: schemas.LeaderboardUpdate
):
    db_leaderboard = db.query(models.Leaderboard).filter(models.Leaderboard.id == leaderboard.id).first()
    if db_leaderboard is None:
        raise ValueError("Leaderboard not found")
    
    school = leaderboard.school
    db_schools = db.query(models.School_Leaderboard).filter(models.School_Leaderboard.leaderboard_id == db_leaderboard.id).all()

    if len(db_schools) != len(school):
        for school_name in school:
            db_school = db.query(models.School_Leaderboard).filter(models.School_Leaderboard.leaderboard_id == db_leaderboard.id).filter(models.School_Leaderboard.school == school_name).first()
            if db_school is None:
                db_school = models.School_Leaderboard(
                    school=school_name,
                    leaderboard_id=db_leaderboard.id
                )
                db.add(db_school)
                db.commit()
    
    return db_leaderboard

def remove_leaderboard_school(
        db: Session,
        leaderboard: schemas.LeaderboardUpdate
):
    db_leaderboard = db.query(models.Leaderboard).filter(models.Leaderboard.id == leaderboard.id).first()
    if db_leaderboard is None:
        raise ValueError("Leaderboard not found")
    
    school = leaderboard.school
    db_schools = db.query(models.School_Leaderboard).filter(models.School_Leaderboard.leaderboard_id == db_leaderboard.id).all()

    if len(db_schools) != len(school):
        for db_school in db_schools:
            if db_school.school not in school:
                db.delete(db_school)
                db.commit()
    
    return db_leaderboard



def add_leaderboard_vocab(
        db: Session,
        leaderboard_id: int,
        vocab: schemas.VocabularyBase
):
    db_leaderboard = db.query(models.Leaderboard).filter(models.Leaderboard.id == leaderboard_id).first()
    if db_leaderboard is None:
        raise ValueError("Leaderboard not found")
    
    db_vocab = db.query(
        models.Vocabulary
    ).filter(
        models.Vocabulary.word == vocab.word
    ).filter(
        models.Vocabulary.pos == vocab.pos
    ).first()
    if db_vocab is None:
        db_vocab = models.Vocabulary(
            word=vocab.word,
            meaning=vocab.meaning,
            pos=vocab.pos
        )
        db.add(db_vocab)
        db.commit()
        db.refresh(db_vocab)

    db_vocab = db.query(
        models.LeaderboardVocabulary
    ).filter(
        models.LeaderboardVocabulary.leaderboard_id == db_leaderboard.id
    ).filter(
        models.LeaderboardVocabulary.vocabulary_id == db_vocab.id
    ).first()

    if db_vocab is None:
        db_vocab = models.LeaderboardVocabulary(
            leaderboard_id=db_leaderboard.id,
            vocabulary_id=db_vocab.id
        )
        db.add(db_vocab)
        db.commit()
    
    return db_leaderboard

def remove_leaderboard_vocab(
        db: Session,
        leaderboard_id: int,
        vocab_id: int
):
    db_leaderboard = db.query(models.Leaderboard).filter(models.Leaderboard.id == leaderboard_id).first()
    if db_leaderboard is None:
        raise ValueError("Leaderboard not found")
    
    db_vocab = db.query(
        models.Vocabulary
    ).filter(
        models.Vocabulary.id == vocab_id
    ).first()
    if db_vocab is None:
        raise ValueError("Vocabulary not found")

    db_vocab = db.query(
        models.LeaderboardVocabulary
    ).filter(
        models.LeaderboardVocabulary.leaderboard_id == db_leaderboard.id
    ).filter(
        models.LeaderboardVocabulary.vocabulary_id == db_vocab.id
    ).first()

    if db_vocab is None:
        raise ValueError("Vocabulary not found in leaderboard")
    
    db.delete(db_vocab)
    db.commit()

    return db_leaderboard
    

def update_leaderboard_difficulty(
        db: Session,
        leaderboard_id: int,
        difficulty_level: int
):
    db_leaderboard = db.query(models.Leaderboard).filter(models.Leaderboard.id == leaderboard_id).first()
    db_leaderboard.difficulty_level = difficulty_level
    db.commit()
    db.refresh(db_leaderboard)
    return db_leaderboard

def delete_leaderboard(db: Session, leaderboard_id: int):
    db_leaderboard = db.query(models.Leaderboard).filter(models.Leaderboard.id == leaderboard_id).first()
    db_original_images = db.query(models.OriginalImage).filter(models.OriginalImage.id == db_leaderboard.original_image_id).all()

    db_rounds = db.query(models.Round).filter(models.Round.leaderboard_id == leaderboard_id).all()

    db_leaderboard_vocab = db.query(
        models.LeaderboardVocabulary
    ).filter(
        models.LeaderboardVocabulary.leaderboard_id == leaderboard_id
    ).all()

    db_description = db.query(models.Description).filter(models.Description.leaderboard_id == leaderboard_id).all()

    db_school = db.query(models.School_Leaderboard).filter(models.School_Leaderboard.leaderboard_id == leaderboard_id).all()

    if db_original_images:
        for image in db_original_images:
            db.delete(image)
        db.commit()

    if db_rounds:
        for round in db_rounds:
            db.delete(round)
        db.commit()

    if db_leaderboard_vocab:
        for vocab in db_leaderboard_vocab:
            db.delete(vocab)
        db.commit()

    if db_school:
        for school in db_school:
            db.delete(school)
        db.commit()

    if db_leaderboard:
        db.delete(db_leaderboard)
        db.commit()
    return db_leaderboard

def get_original_image(db: Session, image_id: int):
    return db.query(models.OriginalImage).filter(models.OriginalImage.id == image_id).first()

def create_original_image(db: Session, image: schemas.ImageBase):
    db_image = models.OriginalImage(**image.model_dump())
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image

def get_interpreted_image(db: Session, image_id: int):
    return db.query(models.InterpretedImage).filter(models.InterpretedImage.id == image_id).first()

def create_interpreted_image(db: Session, image: schemas.ImageBase):
    db_image = models.InterpretedImage(**image.model_dump())
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image

def delete_interpreted_image(db: Session, image_id: int):
    db_image = db.query(models.InterpretedImage).filter(models.InterpretedImage.id == image_id).first()
    if db_image:
        db.delete(db_image)
        db.commit()
    return db_image

def get_story(db: Session, story_id: int):
    return db.query(models.Story).filter(models.Story.id == story_id).first()

def get_stories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Story).offset(skip).limit(limit).all()

def create_story(db: Session, story: schemas.StoryCreate):
    db_story = models.Story(
        **story.model_dump()
    )
    db.add(db_story)
    db.commit()
    db.refresh(db_story)
    return db_story

def get_scenes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Scene).offset(skip).limit(limit).all()

def get_scene(db: Session, scene_id: int = None, scene_name: str = None):
    if scene_name:
        return db.query(models.Scene).filter(models.Scene.name == scene_name).first()
    else:
        return db.query(models.Scene).filter(models.Scene.id == scene_id).first()

def create_scene(db: Session, scene: schemas.SceneBase):
    db_scene = models.Scene(**scene.model_dump())
    db.add(db_scene)
    db.commit()
    db.refresh(db_scene)
    return db_scene

def get_description(db: Session, leaderboard_id: int, model_name: str=None):
    if model_name:
        return db.query(models.Description).filter(models.Description.leaderboard_id == leaderboard_id).filter(models.Description.model == model_name).all()
    else:
        return db.query(models.Description).filter(models.Description.leaderboard_id == leaderboard_id).all()

def create_description(db: Session, description: schemas.DescriptionBase):
    db_description = models.Description(**description.model_dump())
    db.add(db_description)
    db.commit()
    db.refresh(db_description)
    return db_description

def create_program(db: Session, program: schemas.ProgramBase):
    db_program = models.Program(**program.model_dump())
    db.add(db_program)
    db.commit()
    db.refresh(db_program)
    return db_program

def get_programs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Program).offset(skip).limit(limit).all()

def get_program_by_name(db: Session, program_name: str):
    return db.query(models.Program).filter(models.Program.name == program_name).first()

def get_round(db: Session, round_id: int):
    return db.query(models.Round).filter(models.Round.id == round_id).first()

def get_rounds(db: Session, skip: int = 0, limit: int = 100, player_id: int = None,is_completed: bool = True, leaderboard_id: int = None, program_id: int = None):
    if program_id:
        rounds = db.query(
            models.Round,
        ).\
        filter(models.Round.program_id == program_id)
    else:
        rounds = db.query(
            models.Round,
        )

    if leaderboard_id and player_id:
        return rounds.filter(models.Round.is_completed == is_completed).filter(models.Round.leaderboard_id == leaderboard_id).filter(models.Round.player_id==player_id).order_by(models.Round.id.desc()).offset(skip).limit(limit).all()
    elif leaderboard_id:
        return rounds.filter(models.Round.is_completed == is_completed).filter(models.Round.leaderboard_id == leaderboard_id).order_by(models.Round.id.desc()).offset(skip).limit(limit).all()
    elif player_id:
        return rounds.filter(models.Round.is_completed == is_completed).filter(models.Round.player_id==player_id).order_by(models.Round.id.desc()).offset(skip).limit(limit).all()
    else:
        return rounds.filter(models.Round.is_completed == is_completed).order_by(models.Round.id.desc()).offset(skip).limit(limit).all()

def create_round(db: Session, leaderboard_id:int, user_id: int, created_at: datetime.datetime, model_name: str="gpt-4o-mini", program_id: Optional[int]=None):
    db_chat=models.Chat()
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    if program_id:
        db_round = models.Round(
            player_id=user_id,
            chat_history=db_chat.id,
            leaderboard_id=leaderboard_id,
            model=model_name,
            created_at=created_at,
            program_id=program_id,
        )
    else:
        db_round = models.Round(
            player_id=user_id,
            chat_history=db_chat.id,
            leaderboard_id=leaderboard_id,
            model=model_name,
            created_at=created_at,
        )
    
    db.add(db_round)
    db.commit()
    db.refresh(db_round)
    return db_round

def get_generation(db: Session, generation_id: int):
    return db.query(models.Generation).filter(models.Generation.id == generation_id).first()

def get_generations(db: Session, program_id: int=None, skip: int = 0, limit: int = 100, player_id: int = None, leaderboard_id: int = None, order_by: str = "id"):
    if program_id is not None:
        if order_by == "id":
            if leaderboard_id and player_id:
                generations = db.query(
                    models.Generation,
                    models.Round
                ).\
                join(models.Round, models.Generation.round_id == models.Round.id).\
                filter(models.Round.leaderboard_id == leaderboard_id).\
                filter(models.Round.player_id == player_id).\
                filter(models.Generation.is_completed == True).\
                order_by(models.Generation.id.desc()).offset(skip).limit(limit).all()
            elif leaderboard_id:
                generations = db.query(
                    models.Generation,
                    models.Round
                ).\
                join(models.Round, models.Generation.round_id == models.Round.id).\
                filter(models.Round.leaderboard_id == leaderboard_id).\
                filter(models.Round.program_id == program_id).\
                filter(models.Generation.is_completed == True).\
                order_by(models.Generation.id.desc()).offset(skip).limit(limit).all()
            elif player_id:
                generations = db.query(
                    models.Generation,
                    models.Round
                ).\
                join(models.Round, models.Generation.round_id == models.Round.id).\
                filter(models.Round.player_id == player_id).\
                filter(models.Generation.is_completed == True).\
                order_by(models.Generation.id.desc()).offset(skip).limit(limit).all()
            else:
                generations = db.query(
                    models.Generation,
                    models.Round
                ).\
                join(models.Round, models.Generation.round_id == models.Round.id).\
                filter(models.Round.program_id == program_id).\
                filter(models.Generation.is_completed == True).\
                order_by(models.Generation.id.desc()).offset(skip).limit(limit).all()
                
        elif order_by == "total_score":
            if leaderboard_id and player_id:
                generations = db.query(
                    models.Generation,
                    models.Round
                ).\
                join(models.Round, models.Generation.round_id == models.Round.id).\
                filter(models.Round.leaderboard_id == leaderboard_id).\
                filter(models.Round.player_id == player_id).\
                filter(models.Generation.is_completed == True).\
                order_by(models.Generation.total_score.desc()).offset(skip).limit(limit).all()
            elif leaderboard_id:
                generations = db.query(
                    models.Generation,
                    models.Round
                ).\
                join(models.Round, models.Generation.round_id == models.Round.id).\
                filter(models.Round.leaderboard_id == leaderboard_id).\
                filter(models.Round.program_id == program_id).\
                filter(models.Generation.is_completed == True).\
                order_by(models.Generation.total_score.desc()).offset(skip).limit(limit).all()
            elif player_id:
                generations = db.query(
                    models.Generation,
                    models.Round
                ).\
                join(models.Round, models.Generation.round_id == models.Round.id).\
                filter(models.Round.player_id == player_id).\
                filter(models.Generation.is_completed == True).\
                order_by(models.Generation.total_score.desc()).offset(skip).limit(limit).all()
            else:
                generations = db.query(
                    models.Generation,
                    models.Round
                ).\
                join(models.Round, models.Generation.round_id == models.Round.id).\
                filter(models.Round.program_id == program_id).\
                filter(models.Generation.is_completed == True).\
                order_by(models.Generation.total_score.desc()).offset(skip).limit(limit).all()
        else:
            raise ValueError("Invalid order_by value")
        return generations
    if order_by == "id":
        if leaderboard_id and player_id:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            filter(models.Round.leaderboard_id == leaderboard_id).\
            filter(models.Round.player_id == player_id).\
            filter(models.Generation.is_completed == True).\
            order_by(models.Generation.id.desc()).offset(skip).limit(limit).all()
        elif leaderboard_id:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            filter(models.Round.leaderboard_id == leaderboard_id).\
            filter(models.Generation.is_completed == True).\
            order_by(models.Generation.id.desc()).offset(skip).limit(limit).all()
        elif player_id:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            filter(models.Round.player_id == player_id).\
            filter(models.Generation.is_completed == True).\
            order_by(models.Generation.id.desc()).offset(skip).limit(limit).all()
        else:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            filter(models.Generation.is_completed == True).\
            order_by(models.Generation.id.desc()).offset(skip).limit(limit).all()
            
    elif order_by == "total_score":
        if leaderboard_id and player_id:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            filter(models.Round.leaderboard_id == leaderboard_id).\
            filter(models.Round.player_id == player_id).\
            filter(models.Generation.is_completed == True).\
            order_by(models.Generation.total_score.desc()).offset(skip).limit(limit).all()
        elif leaderboard_id:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            filter(models.Round.leaderboard_id == leaderboard_id).\
            filter(models.Generation.is_completed == True).\
            order_by(models.Generation.total_score.desc()).offset(skip).limit(limit).all()
        elif player_id:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            filter(models.Round.player_id == player_id).\
            filter(models.Generation.is_completed == True).\
            order_by(models.Generation.total_score.desc()).offset(skip).limit(limit).all()
        else:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            filter(models.Generation.is_completed == True).\
            order_by(models.Generation.total_score.desc()).offset(skip).limit(limit).all()
    else:
        raise ValueError("Invalid order_by value")
    return generations

def get_generations_by_ids(db: Session, generation_ids: List[int]):
    if not generation_ids:
        return []
    return db.query(models.Generation).filter(models.Generation.id.in_(generation_ids)).all()

def create_generation(db: Session, round_id: int, generation: schemas.GenerationCreate):
    db_round = db.query(models.Round).filter(models.Round.id == round_id).first()
    
    db_generation = models.Generation(
        **generation.model_dump()
    )
    db.add(db_generation)
    db.commit()
    db.refresh(db_generation)

    db_round.last_generation_id = db_generation.id
    
    db.commit()
    db.refresh(db_round)
    return db_generation

def update_generation0(db: Session, generation: schemas.GenerationCreate, generation_id: int):
    db_generation = db.query(models.Generation).filter(models.Generation.id == generation_id).first()
    db_generation.created_at = generation.created_at
    db_generation.sentence = generation.sentence
    db.commit()
    db.refresh(db_generation)
    return db_generation

def update_generation1(db: Session, generation: schemas.GenerationCorrectSentence):
    db_generation = db.query(models.Generation).filter(models.Generation.id == generation.id).first()
    db_generation.correct_sentence = generation.correct_sentence
    db.commit()
    db.refresh(db_generation)
    return db_generation

def update_generation2(db: Session, generation: schemas.GenerationInterpretation):
    db_generation = db.query(models.Generation).filter(models.Generation.id == generation.id).first()
    if not db_generation:
        raise ValueError("Generation not found")
    db_generation.interpreted_image_id = generation.interpreted_image_id
    db.commit()
    db.refresh(db_generation)
    return db_generation

def update_generation3(db: Session, generation: schemas.GenerationComplete):
    
    db.bulk_update_mappings(models.Generation, [generation.model_dump(exclude_none=True)])
    db.commit()
    db_generation = db.query(models.Generation).filter(models.Generation.id == generation.id).first()
    return db_generation

def create_score(db: Session, score: schemas.ScoreCreate, generation_id: int):
    db_score = models.Score(
        **score.model_dump()
    )
    db.add(db_score)
    db.commit()
    db.refresh(db_score)

    db_generation = db.query(models.Generation).filter(models.Generation.id == generation_id).first()
    db_generation.score_id = db_score.id
    db.commit()
    db.refresh(db_generation)

    return db_score

def update_score(db: Session, score: schemas.ScoreUpdate):
    db_score = db.query(models.Score).filter(models.Score.id == score.id).first()
    db_score.image_similarity = score.image_similarity
    db.commit()
    db.refresh(db_score)
    return db_score

def delete_score(db: Session, score_id: int):
    db_score = db.query(models.Score).filter(models.Score.id == score_id).first()
    if db_score:
        db.delete(db_score)
        db.commit()
    return db_score

def get_score(db: Session, score_id: Optional[int] = None, generation_id: Optional[int] = None):
    if score_id:
        return db.query(models.Score).filter(models.Score.id == score_id).first()
    elif generation_id:
        return db.query(models.Score).filter(models.Score.generation_id == generation_id).first()
    else:
        return None

def complete_round(db: Session, round_id: int, round: schemas.RoundComplete):
    db.bulk_update_mappings(models.Round, [round.model_dump()])
    db.commit()
    db_round = db.query(models.Round).filter(models.Round.id == round_id).first()
    return db_round

def get_chat(db: Session, chat_id: int):
    return db.query(models.Chat).filter(models.Chat.id == chat_id).first()

def create_message(db: Session, message: schemas.MessageBase, chat_id: int):
    db_message = models.Message(
        **message.model_dump()
    )
    db_message.chat_id = chat_id
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    db_chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    db_chat.messages.append(db_message)
    db.commit()
    db.refresh(db_chat)
    return {"message": db_message, "chat": db_chat}

def get_chat_messages_by_ids(db: Session, message_ids: List[int]):
    return db.query(models.Message).filter(models.Message.id.in_(message_ids)).all()

def get_vocabulary(db: Session, vocabulary: str, part_of_speech: str=None):
    if part_of_speech is None:
        return db.query(models.Vocabulary).filter(models.Vocabulary.word == vocabulary).all()
    return db.query(models.Vocabulary).filter(models.Vocabulary.word == vocabulary).filter(models.Vocabulary.pos == part_of_speech).first()

def get_vocabularies(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Vocabulary).offset(skip).limit(limit).all()

def create_vocabulary(db: Session, vocabulary: schemas.VocabularyBase):
    db_vocabulary = models.Vocabulary(**vocabulary.model_dump())
    db.add(db_vocabulary)
    db.commit()
    db.refresh(db_vocabulary)
    return db_vocabulary

def get_vocab_saved_time(db: Session, vocabulary_id: int):
    return db.query(models.PersonalDictionary).filter(models.PersonalDictionary.vocabulary == vocabulary_id).count()

def get_personal_dictionary(db: Session, player_id: int, vocabulary_id: int):
    return db.query(models.PersonalDictionary).filter(models.PersonalDictionary.player == player_id).filter(models.PersonalDictionary.vocabulary == vocabulary_id).first()

def create_personal_dictionary(
        db: Session, 
        user_id: int,
        vocabulary_id: int,
        round_id: int,
        created_at: datetime.datetime
):
    db_dictionary = models.PersonalDictionary(
        player=user_id,
        vocabulary=vocabulary_id,
        save_at_round_id=round_id,
        created_at=created_at
    )

    db.add(db_dictionary)
    db.commit()
    db.refresh(db_dictionary)
    return db_dictionary

def update_personal_dictionary(
        db: Session,
        dictionary: schemas.PersonalDictionaryUpdate
):
    db.bulk_update_mappings(models.PersonalDictionary, [dictionary.model_dump()])
    db.commit()
    db_dictionary = db.query(models.PersonalDictionary).\
        filter(models.PersonalDictionary.player == dictionary.player).\
            filter(models.PersonalDictionary.vocabulary == dictionary.vocabulary).\
                first()
    return db_dictionary

def update_personal_dictionary_used(
        db: Session,
        dictionary: schemas.PersonalDictionaryId
):
    db_dictionary = db.query(models.PersonalDictionary).filter(models.PersonalDictionary.player == dictionary.player).filter(models.PersonalDictionary.vocabulary == dictionary.vocabulary).first()
    db_dictionary.used_times += 1
    db.commit()
    db.refresh(db_dictionary)
    return db_dictionary

def delete_personal_dictionary(
        db: Session,
        player_id: int,
        vocabulary_id: int
):
    db_dictionary = db.query(models.PersonalDictionary).filter(models.PersonalDictionary.player == player_id).filter(models.PersonalDictionary.vocabulary == vocabulary_id).first()
    if db_dictionary:
        db.delete(db_dictionary)
        db.commit()
    return db_dictionary

def get_leaderboard_vocabulary(db: Session, leaderboard_id: int, vocabulary_id: int):
    return db.query(models.LeaderboardVocabulary).filter(models.LeaderboardVocabulary.leaderboard_id == leaderboard_id).filter(models.LeaderboardVocabulary.vocabulary_id == vocabulary_id).first()

def create_leaderboard_vocabulary(
        db: Session, 
        leaderboard_id: int,
        vocabulary_id: int
):
    db_leaderboard_vocabulary = models.LeaderboardVocabulary(
        leaderboard_id=leaderboard_id,
        vocabulary_id=vocabulary_id
    )

    db.add(db_leaderboard_vocabulary)
    db.commit()
    db.refresh(db_leaderboard_vocabulary)
    return db_leaderboard_vocabulary

def get_goodoriginal(db: Session, player_id: int, original_id: int):
    return db.query(models.GoodOriginal).filter(models.GoodOriginal.player_id == player_id).filter(models.GoodOriginal.original_id == original_id).first()

def create_goodoriginal(db: Session, user_id: int, image_id: int):
    db_goodoriginal = models.GoodOriginal(
        player_id=user_id,
        original_id=image_id
    )
    db.add(db_goodoriginal)
    db.commit()
    db.refresh(db_goodoriginal)
    return db_goodoriginal

def get_goodinterpreted(db: Session, player_id: int, interpreted_id: int):
    return db.query(models.GoodInterpreted).filter(models.GoodInterpreted.player_id == player_id).filter(models.GoodInterpreted.interpreted_id == interpreted_id).first()

def create_goodinterpreted(db: Session, user_id: int, image_id: int):
    db_goodinterpreted = models.GoodInterpreted(
        player_id=user_id,
        interpreted_id=image_id
    )
    db.add(db_goodinterpreted)
    db.commit()
    db.refresh(db_goodinterpreted)
    return db_goodinterpreted

def get_goodround(db: Session, player_id: int, round_id: int):
    return db.query(models.GoodRound).filter(models.GoodRound.player_id == player_id).filter(models.GoodRound.round_id == round_id).first()

def create_goodround(db: Session, user_id: int, round_id: int):
    db_goodround = models.GoodRound(
        player_id=user_id,
        round_id=round_id
    )
    db.add(db_goodround)
    db.commit()
    db.refresh(db_goodround)
    return db_goodround

def create_task(db: Session, task: schemas.Task):
    db_task = models.Task(
        id = task.id,
        generation_id = task.generation_id,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_task(db: Session, task_id: int):
    return db.query(models.Task).filter(models.Task.id == task_id).first()

def get_tasks(db: Session, generation_id: Optional[int] = None, leaderboard_id: Optional[int] = None):
    if generation_id:
        return db.query(models.Task).filter(models.Task.generation_id == generation_id).all()
    elif leaderboard_id:
        return db.query(models.Task).filter(models.Task.leaderboard_id == leaderboard_id).all()
    else:
        return db.query(models.Task).all()
    
def delete_task(db: Session, task_id: int):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task:
        db.delete(db_task)
        db.commit()
    return db_task

def delete_all_tasks(db: Session):
    db_tasks = db.query(models.Task).all()
    if db_tasks:
        for task in db_tasks:
            db.delete(task)
        db.commit()
    return db_tasks

def get_all_tasks(db: Session):
    return db.query(models.Task).all()

def get_error_task(db: Session, group_type: str):
    
    guest_ids = db.query(models.User).filter(models.User.username.like('%guest%')).all()

    answer_input_generation = db.query(models.Generation).\
        filter(models.Generation.correct_sentence != None).\
        filter(
            models.Generation.round.has(
                models.Round.player_id.notin_([guest.id for guest in guest_ids])
            )
        )
    
    if group_type == 'no_interpretation':
        image_group = db.query(models.InterpretedImage).\
            filter(or_(models.InterpretedImage.image == None,
                       models.InterpretedImage.generation == None)).\
                all()
        return image_group

    if group_type == 'no_image':
        # correct_sentence is set but interpreted_image_id is not set
        generation_group = answer_input_generation.\
            filter(models.Generation.interpreted_image == None).\
                all()
        return generation_group

    if group_type == 'no_score':
        # the score are not calculated
        generation_group = answer_input_generation.\
            filter(models.Generation.score_id == None).\
                all()
        return generation_group
    if group_type == 'no_content_score':
        # content_score is not calculated
        generation_group = answer_input_generation.\
            filter(
                models.Generation.updated_content_score != True,
            ).\
                all()
        return generation_group
    if group_type == 'no_word_num':
        # word_num is not calculated
        generation_group = answer_input_generation.\
            filter(
                or_(
                    models.Generation.updated_n_words != True,
                    models.Generation.n_words == 0,
                )
            ).\
                all()
        return generation_group
    if group_type == 'no_grammar':
        # grammar_score is not calculated
        generation_group = answer_input_generation.\
            filter(
                models.Generation.updated_grammar_errors != True
            ).\
                all()
        return generation_group
    if group_type == 'no_perplexity':
        # perplexity is not calculated
        generation_group = answer_input_generation.\
            filter(
                models.Generation.updated_perplexity != True
            ).\
                all()
        return generation_group
    
    if group_type == 'no_similarity':
        # image_similarity is not set
        score_group = db.query(models.Score).\
            filter(or_(
                models.Score.image_similarity == None,
                models.Score.image_similarity == 0
            )).\
            filter(
                models.Score.generation_id.in_(
                    db.query(models.Generation.id).\
                        filter(models.Generation.content_score > 0, models.Generation.interpreted_image_id != None)
            )).\
                all()
        return score_group
    
    if group_type == 'no_complete':
        # the generation is not completed
        generation_group = answer_input_generation.\
            filter(models.Generation.is_completed != True).\
                all()
        return generation_group
    
def create_user_action(db: Session, user_action: schemas.UserActionBase):
    db_user_action = models.User_Action(
        **user_action.model_dump()
    )
    db.add(db_user_action)
    db.commit()
    db.refresh(db_user_action)
    return db_user_action

def update_user_action(db: Session, user_action: schemas.UserActionUpdate):
    db.bulk_update_mappings(models.User_Action, [user_action.model_dump(exclude_none=True)])
    db.commit()
    db_user_action = db.query(models.User_Action).filter(models.User_Action.id == user_action.id).first()
    return db_user_action

def read_user_action(
        db: Session,
        user_id: Optional[int] = None,
        action_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
):
    if user_id and action_type:
        return db.query(models.User_Action).filter(models.User_Action.user_id == user_id).filter(models.User_Action.action_type == action_type).offset(skip).limit(limit).all()
    elif user_id:
        return db.query(models.User_Action).filter(models.User_Action.user_id == user_id).offset(skip).limit(limit).all()
    elif action_type:
        return db.query(models.User_Action).filter(models.User_Action.action_type == action_type).offset(skip).limit(limit).all()
    else:
        return db.query(models.User_Action).offset(skip).limit(limit).all()
    
# CRUD operations for analytics
def create_word_cloud(
        db: Session,
        cloud_type: Literal['mistake', 'writing', 'user_chat', 'assistant_chat'],
        word_cloud: schemas.WordCloudCreate
):
    db_word_cloud = models.WordCloud(
        latest_generation_id=word_cloud.latest_generation_id,
        last_updated=word_cloud.last_updated,
    )
    db.add(db_word_cloud)
    db.commit()
    db.refresh(db_word_cloud)
    if cloud_type == 'mistake':
        for item in word_cloud.items:
            db_word_cloud_item = models.MistakeWordCloudItem(
                word=item.word,
                frequency=item.frequency,
                color=item.color,
                word_cloud_id=db_word_cloud.id,
            )
            db.add(db_word_cloud_item)
            db.commit()
    elif cloud_type == 'writing':
        for item in word_cloud.items:
            db_word_cloud_item = models.WritingWordCloudItem(
                word=item.word,
                frequency=item.frequency,
                color=item.color,
                word_cloud_id=db_word_cloud.id,
            )
            db.add(db_word_cloud_item)
            db.commit()
    elif cloud_type == 'user_chat':
        for item in word_cloud.items:
            db_word_cloud_item = models.UserChatWordCloudItem(
                word=item.word,
                frequency=item.frequency,
                color=item.color,
                word_cloud_id=db_word_cloud.id,
            )
            db.add(db_word_cloud_item)
            db.commit()
    elif cloud_type == 'assistant_chat':
        for item in word_cloud.items:
            db_word_cloud_item = models.AssistantChatWordCloudItem(
                word=item.word,
                frequency=item.frequency,
                color=item.color,
                word_cloud_id=db_word_cloud.id,
            )
            db.add(db_word_cloud_item)
            db.commit()
    db.refresh(db_word_cloud)
    return db_word_cloud

def create_word_cloud_item_generation(
        db: Session,
        cloud_type: Literal['mistake', 'writing', 'user_chat', 'assistant_chat'],
        word_cloud_item_id: int,
        generation_or_message_id: int
):
    if cloud_type == 'mistake':
        db_word_cloud_item_generation = db.query(models.MistakeWordCloudItemGeneration).filter(
            models.MistakeWordCloudItemGeneration.word_cloud_item_id == word_cloud_item_id,
            models.MistakeWordCloudItemGeneration.generation_id == generation_or_message_id
        ).first()
        if db_word_cloud_item_generation:
            return db_word_cloud_item_generation
        
        db_word_cloud_item_generation = models.MistakeWordCloudItemGeneration(
            word_cloud_item_id=word_cloud_item_id,
            generation_id=generation_or_message_id
        )

        db.add(db_word_cloud_item_generation)
        db.commit()
        db.refresh(db_word_cloud_item_generation)
        return db_word_cloud_item_generation
    elif cloud_type == 'writing':
        db_word_cloud_item_generation = db.query(models.WritingWordCloudItemGeneration).filter(
            models.WritingWordCloudItemGeneration.word_cloud_item_id == word_cloud_item_id,
            models.WritingWordCloudItemGeneration.generation_id == generation_or_message_id
        ).first()
        if db_word_cloud_item_generation:
            return db_word_cloud_item_generation
        db_word_cloud_item_generation = models.WritingWordCloudItemGeneration(
            word_cloud_item_id=word_cloud_item_id,
            generation_id=generation_or_message_id
        )

        db.add(db_word_cloud_item_generation)
        db.commit()
        db.refresh(db_word_cloud_item_generation)
        return db_word_cloud_item_generation
    elif cloud_type == 'user_chat':
        db_word_cloud_item_generation = db.query(models.UserChatWordCloudItemChat).filter(
            models.UserChatWordCloudItemChat.word_cloud_item_id == word_cloud_item_id,
            models.UserChatWordCloudItemChat.message_id == generation_or_message_id
        ).first()
        if db_word_cloud_item_generation:
            return db_word_cloud_item_generation
        db_word_cloud_item_generation = models.UserChatWordCloudItemChat(
            word_cloud_item_id=word_cloud_item_id,
            message_id=generation_or_message_id
        )

        db.add(db_word_cloud_item_generation)
        db.commit()
        db.refresh(db_word_cloud_item_generation)
        return db_word_cloud_item_generation
    elif cloud_type == 'assistant_chat':
        db_word_cloud_item_generation = db.query(models.AssistantChatWordCloudItemChat).filter(
            models.AssistantChatWordCloudItemChat.word_cloud_item_id == word_cloud_item_id,
            models.AssistantChatWordCloudItemChat.message_id == generation_or_message_id
        ).first()
        if db_word_cloud_item_generation:
            return db_word_cloud_item_generation
        db_word_cloud_item_generation = models.AssistantChatWordCloudItemChat(
            word_cloud_item_id=word_cloud_item_id,
            message_id=generation_or_message_id
        )

        db.add(db_word_cloud_item_generation)
        db.commit()
        db.refresh(db_word_cloud_item_generation)
        return db_word_cloud_item_generation
    return None

def get_word_cloud_item_by_word(
        db: Session,
        word: str,
        word_cloud_id: int,
        cloud_type: Literal['mistake', 'writing', 'user_chat', 'assistant_chat']
):
    if cloud_type == 'mistake':
        return db.query(models.MistakeWordCloudItem).filter(models.MistakeWordCloudItem.word == word, models.MistakeWordCloudItem.word_cloud_id == word_cloud_id).first()
    elif cloud_type == 'writing':
        return db.query(models.WritingWordCloudItem).filter(models.WritingWordCloudItem.word == word, models.WritingWordCloudItem.word_cloud_id == word_cloud_id).first()
    elif cloud_type == 'user_chat':
        return db.query(models.UserChatWordCloudItem).filter(models.UserChatWordCloudItem.word == word, models.UserChatWordCloudItem.word_cloud_id == word_cloud_id).first()
    elif cloud_type == 'assistant_chat':
        return db.query(models.AssistantChatWordCloudItem).filter(models.AssistantChatWordCloudItem.word == word, models.AssistantChatWordCloudItem.word_cloud_id == word_cloud_id).first()
    return None

def get_word_cloud_item_generation(
        db: Session,
        cloud_type: Literal['mistake', 'writing', 'user_chat', 'assistant_chat'],
        word_cloud_item_id: Optional[int] = None,
):
    if cloud_type == 'mistake':
        return db.query(models.MistakeWordCloudItemGeneration).filter(models.MistakeWordCloudItemGeneration.word_cloud_item_id == word_cloud_item_id).all()
    elif cloud_type == 'writing':
        return db.query(models.WritingWordCloudItemGeneration).filter(models.WritingWordCloudItemGeneration.word_cloud_item_id == word_cloud_item_id).all()
    elif cloud_type == 'user_chat':
        return db.query(models.UserChatWordCloudItemChat).filter(models.UserChatWordCloudItemChat.word_cloud_item_id == word_cloud_item_id).all()
    elif cloud_type == 'assistant_chat':
        return db.query(models.AssistantChatWordCloudItemChat).filter(models.AssistantChatWordCloudItemChat.word_cloud_item_id == word_cloud_item_id).all()
    return None

def update_word_cloud(
        db: Session,
        cloud_type: Literal['mistake', 'writing', 'user_chat', 'assistant_chat'],
        word_cloud: schemas.WordCloudUpdate
):
    db.bulk_update_mappings(models.WordCloud, [word_cloud.model_dump(exclude_none=True)])
    db.commit()
    db_word_cloud = db.query(models.WordCloud).filter(models.WordCloud.id == word_cloud.id).first()
    
    if cloud_type == 'mistake':
        for item in word_cloud.items:
            db_word_cloud_item = db.query(models.MistakeWordCloudItem).filter(models.MistakeWordCloudItem.word_cloud_id == word_cloud.id).\
            filter(models.MistakeWordCloudItem.word == item.word).first()
            if db_word_cloud_item is None:
                db_word_cloud_item = models.MistakeWordCloudItem(
                    word=item.word,
                    frequency=item.frequency,
                    color=item.color,
                    word_cloud_id=db_word_cloud.id,
                )
                db.add(db_word_cloud_item)
                db.commit()
            else:
                db_word_cloud_item.frequency += item.frequency
                db.commit()
    elif cloud_type == 'writing':
        for item in word_cloud.items:
            db_word_cloud_item = db.query(models.WritingWordCloudItem).filter(models.WritingWordCloudItem.word_cloud_id == word_cloud.id).\
            filter(models.WritingWordCloudItem.word == item.word).first()
            if db_word_cloud_item is None:
                db_word_cloud_item = models.WritingWordCloudItem(
                    word=item.word,
                    frequency=item.frequency,
                    color=item.color,
                    word_cloud_id=db_word_cloud.id,
                )
                db.add(db_word_cloud_item)
                db.commit()
            else:
                db_word_cloud_item.frequency += item.frequency
                db.commit()
    elif cloud_type == 'user_chat':
        for item in word_cloud.items:
            db_word_cloud_item = db.query(models.UserChatWordCloudItem).filter(models.UserChatWordCloudItem.word_cloud_id == word_cloud.id).\
            filter(models.UserChatWordCloudItem.word == item.word).first()
            if db_word_cloud_item is None:
                db_word_cloud_item = models.UserChatWordCloudItem(
                    word=item.word,
                    frequency=item.frequency,
                    color=item.color,
                    word_cloud_id=db_word_cloud.id,
                )
                db.add(db_word_cloud_item)
                db.commit()
            else:
                db_word_cloud_item.frequency += item.frequency
                db.commit()
    elif cloud_type == 'assistant_chat':
        for item in word_cloud.items:
            db_word_cloud_item = db.query(models.AssistantChatWordCloudItem).filter(models.AssistantChatWordCloudItem.word_cloud_id == word_cloud.id).\
            filter(models.AssistantChatWordCloudItem.word == item.word).first()
            if db_word_cloud_item is None:
                db_word_cloud_item = models.AssistantChatWordCloudItem(
                    word=item.word,
                    frequency=item.frequency,
                    color=item.color,
                    word_cloud_id=db_word_cloud.id,
                )
                db.add(db_word_cloud_item)
                db.commit()
            else:
                db_word_cloud_item.frequency += item.frequency
                db.commit()
    db.refresh(db_word_cloud)
    return db_word_cloud

def delete_word_cloud_item_generation(
        db: Session,
        cloud_type: Literal['mistake', 'writing', 'user_chat', 'assistant_chat'],
        word_cloud_item_id: int,
        generation_or_message_id: int
):
    if cloud_type == 'mistake':
        db_word_cloud_item_generation = db.query(models.MistakeWordCloudItemGeneration).\
            filter(models.MistakeWordCloudItemGeneration.word_cloud_item_id == word_cloud_item_id).\
            filter(models.MistakeWordCloudItemGeneration.generation_id == generation_or_message_id).first()
    elif cloud_type == 'writing':
        db_word_cloud_item_generation = db.query(models.WritingWordCloudItemGeneration).\
            filter(models.WritingWordCloudItemGeneration.word_cloud_item_id == word_cloud_item_id).\
            filter(models.WritingWordCloudItemGeneration.generation_id == generation_or_message_id).first()
    elif cloud_type == 'user_chat':
        db_word_cloud_item_generation = db.query(models.UserChatWordCloudItemChat).\
            filter(models.UserChatWordCloudItemChat.word_cloud_item_id == word_cloud_item_id).\
            filter(models.UserChatWordCloudItemChat.message_id == generation_or_message_id).first()
    elif cloud_type == 'assistant_chat':
        db_word_cloud_item_generation = db.query(models.AssistantChatWordCloudItemChat).\
            filter(models.AssistantChatWordCloudItemChat.word_cloud_item_id == word_cloud_item_id).\
            filter(models.AssistantChatWordCloudItemChat.message_id == generation_or_message_id).first()
        
    if db_word_cloud_item_generation:
        db.delete(db_word_cloud_item_generation)
        db.commit()
        return db_word_cloud_item_generation
    
def read_word_cloud(
        db: Session,
        id: int
):
    db_word_cloud = db.query(models.WordCloud).filter(models.WordCloud.id == id).first()
    return db_word_cloud

def create_leaderboard_analysis(
        db: Session, 
        leaderboard_analysis: schemas.LeaderboardAnalysisCreate
):
    db_leaderboard_analysis = models.Leaderboard_Analysis(
        **leaderboard_analysis.model_dump()
    )
    db.add(db_leaderboard_analysis)
    db.commit()
    db.refresh(db_leaderboard_analysis)
    return db_leaderboard_analysis

def create_leaderboard_analysis_word_cloud(
        db: Session, 
        leaderboard_analysis_word_cloud: schemas.LeaderboardAnalysis_WordCloudCreate
):
    db_leaderboard_analysis_word_cloud = models.LeaderboardAnalysis_WordCloud(
        **leaderboard_analysis_word_cloud.model_dump()
    )
    db.add(db_leaderboard_analysis_word_cloud)
    db.commit()
    db.refresh(db_leaderboard_analysis_word_cloud)
    return db_leaderboard_analysis_word_cloud

def read_leaderboard_analysis(
        db: Session,
        leaderboard_id: int,
        program_id: Optional[int] = None,
):
    db_leaderboard_analysis = db.query(models.Leaderboard_Analysis).\
        filter(models.Leaderboard_Analysis.leaderboard_id == leaderboard_id)
    
    if program_id:
        db_leaderboard_analysis = db_leaderboard_analysis.filter(models.Leaderboard_Analysis.program_id == program_id)
    
    return db_leaderboard_analysis.first()

def read_leaderboard_analysis_word_cloud(
        db: Session,
        leaderboard_analysis_id: int,
        cloud_type: Optional[Literal['mistake', 'writing', 'user_chat', 'assistant_chat']] = 'mistake',
        lang: Optional[str] = 'en',
        require_num: Optional[int] = 1
):
    db_leaderboardanalysis_wordcloud = db.query(models.LeaderboardAnalysis_WordCloud).\
        filter(models.LeaderboardAnalysis_WordCloud.leaderboard_analysis_id == leaderboard_analysis_id)
    if cloud_type:
        db_leaderboardanalysis_wordcloud = db_leaderboardanalysis_wordcloud.filter(models.LeaderboardAnalysis_WordCloud.type == cloud_type)
    if lang:
        db_leaderboardanalysis_wordcloud = db_leaderboardanalysis_wordcloud.filter(models.LeaderboardAnalysis_WordCloud.lang == lang)

    if require_num == 1:
        return db_leaderboardanalysis_wordcloud.first()
    elif require_num > 1:
        return db_leaderboardanalysis_wordcloud.limit(require_num).all()
    

def delete_word_cloud(
        db: Session,
        id: int
):
    db_word_cloud = db.query(models.WordCloud).filter(models.WordCloud.id == id).first()
    if db_word_cloud is None:
        return None
    
    db_leaderboard_analysis_word_clouds = db.query(models.LeaderboardAnalysis_WordCloud).filter(models.LeaderboardAnalysis_WordCloud.word_cloud_id == id).first()
    
    cloud_type = db_leaderboard_analysis_word_clouds.type if db_leaderboard_analysis_word_clouds else None

    # Delete all connections to leaderboard analysis word clouds
    db_leaderboard_analysis_word_clouds = db.query(models.LeaderboardAnalysis_WordCloud).filter(models.LeaderboardAnalysis_WordCloud.word_cloud_id == id).delete(synchronize_session=False)
    db.commit()

    # Delete all word cloud items and their connections to generations or messages
    if cloud_type == 'mistake':
        db_word_cloud_items = db.query(models.MistakeWordCloudItem).filter(models.MistakeWordCloudItem.word_cloud_id == id)
    elif cloud_type == 'writing':
        db_word_cloud_items = db.query(models.WritingWordCloudItem).filter(models.WritingWordCloudItem.word_cloud_id == id)
    elif cloud_type == 'user_chat':
        db_word_cloud_items = db.query(models.UserChatWordCloudItem).filter(models.UserChatWordCloudItem.word_cloud_id == id)
    elif cloud_type == 'assistant_chat':
        db_word_cloud_items = db.query(models.AssistantChatWordCloudItem).filter(models.AssistantChatWordCloudItem.word_cloud_id == id)
    else:
        db_word_cloud_items = None

    if db_word_cloud_items:
        for db_word_cloud_item in db_word_cloud_items.all():
            if cloud_type == 'mistake':
                db_word_cloud_item_generations = db.query(models.MistakeWordCloudItemGeneration).filter(models.MistakeWordCloudItemGeneration.word_cloud_item_id == db_word_cloud_item.id).delete(synchronize_session=False)
            elif cloud_type == 'writing':
                db_word_cloud_item_generations = db.query(models.WritingWordCloudItemGeneration).filter(models.WritingWordCloudItemGeneration.word_cloud_item_id == db_word_cloud_item.id).delete(synchronize_session=False)
            elif cloud_type == 'user_chat':
                db_word_cloud_item_generations = db.query(models.UserChatWordCloudItemChat).filter(models.UserChatWordCloudItemChat.word_cloud_item_id == db_word_cloud_item.id).delete(synchronize_session=False)
            elif cloud_type == 'assistant_chat':
                db_word_cloud_item_generations = db.query(models.AssistantChatWordCloudItemChat).filter(models.AssistantChatWordCloudItemChat.word_cloud_item_id == db_word_cloud_item.id).delete(synchronize_session=False)
    
        db_word_cloud_items.delete(synchronize_session=False)
        db.commit()

    # Finally delete the word cloud itself
    if db_word_cloud:
        db.delete(db_word_cloud)
        db.commit()
    return db_word_cloud

def update_word_cloud_item_color(
        db: Session,
        cloud_type: Literal['mistake', 'writing', 'user_chat', 'assistant_chat'],
        word_cloud_item_id: int,
        color: str
):
    if cloud_type == 'mistake':
        db_word_cloud_item = db.query(models.MistakeWordCloudItem).\
            filter(models.MistakeWordCloudItem.id == word_cloud_item_id).first()
    elif cloud_type == 'writing':
        db_word_cloud_item = db.query(models.WritingWordCloudItem).\
            filter(models.WritingWordCloudItem.id == word_cloud_item_id).first()
    elif cloud_type == 'user_chat':
        db_word_cloud_item = db.query(models.UserChatWordCloudItem).\
            filter(models.UserChatWordCloudItem.id == word_cloud_item_id).first()
    elif cloud_type == 'assistant_chat':
        db_word_cloud_item = db.query(models.AssistantChatWordCloudItem).\
            filter(models.AssistantChatWordCloudItem.id == word_cloud_item_id).first()
        
    if db_word_cloud_item:
        db_word_cloud_item.color = color
        db.commit()
        db.refresh(db_word_cloud_item)
        return db_word_cloud_item
    return None