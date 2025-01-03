from sqlalchemy.orm import Session

from . import models, schemas

from typing import Union, Optional
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
):
    if school_name:
        school_leaderboards = db.query(
            models.Leaderboard,
            models.School_Leaderboard
        ).\
        filter(models.School_Leaderboard.school_name == school_name).\
        join(
            models.Leaderboard,
            models.Leaderboard.id == models.School_Leaderboard.leaderboard_id
        )
    else:
        school_leaderboards = db.query(
            models.Leaderboard
        )

    if published_at_start is None and published_at_end is None:
        return school_leaderboards.\
            filter(models.Leaderboard.published_at <= datetime.datetime.now()).\
                offset(skip).limit(limit).all()
    elif published_at_start is None:
        return school_leaderboards.\
            filter(models.Leaderboard.published_at <= published_at_end).\
                offset(skip).limit(limit).all()
    elif published_at_end is None:
        published_at_end = datetime.datetime.now()
    return school_leaderboards.\
        filter(models.Leaderboard.published_at >= published_at_start).\
            filter(models.Leaderboard.published_at <= published_at_end).\
                offset(skip).limit(limit).all()

    # if published_at_start is None and published_at_end is None:
    #     return db.query(models.Leaderboard).\
    #         filter(models.Leaderboard.published_at <= datetime.datetime.now()).\
    #             offset(skip).limit(limit).all()
    # elif published_at_start is None:
    #     return db.query(models.Leaderboard).\
    #         filter(models.Leaderboard.published_at <= published_at_end).\
    #             offset(skip).limit(limit).all()
    # elif published_at_end is None:
    #     published_at_end = datetime.datetime.now()
    # return db.query(models.Leaderboard).\
    #     filter(models.Leaderboard.published_at >= published_at_start).\
    #         filter(models.Leaderboard.published_at <= published_at_end).\
    #             offset(skip).limit(limit).all()

def get_leaderboard(db: Session, leaderboard_id: int):
    return db.query(models.Leaderboard).filter(models.Leaderboard.id == leaderboard_id).first()

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

def get_round(db: Session, round_id: int):
    return db.query(models.Round).filter(models.Round.id == round_id).first()

def get_rounds(db: Session, skip: int = 0, limit: int = 100, player_id: int = None,is_completed: bool = True, leaderboard_id: int = None):
    if leaderboard_id and player_id:
        return db.query(models.Round).filter(models.Round.is_completed == is_completed).filter(models.Round.leaderboard_id == leaderboard_id).filter(models.Round.player_id==player_id).order_by(models.Round.id.desc()).offset(skip).limit(limit).all()
    elif leaderboard_id:
        return db.query(models.Round).filter(models.Round.is_completed == is_completed).filter(models.Round.leaderboard_id == leaderboard_id).order_by(models.Round.id.desc()).offset(skip).limit(limit).all()
    elif player_id:
        return db.query(models.Round).filter(models.Round.is_completed == is_completed).filter(models.Round.player_id==player_id).order_by(models.Round.id.desc()).offset(skip).limit(limit).all()
    else:
        return db.query(models.Round).filter(models.Round.is_completed == is_completed).order_by(models.Round.id.desc()).offset(skip).limit(limit).all()

def create_round(db: Session, leaderboard_id:int, user_id: int, created_at: datetime.datetime, model_name: str="gpt-4o-mini"):
    db_chat=models.Chat()
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)

    db_round = models.Round(
        player_id=user_id,
        chat_history=db_chat.id,
        leaderboard_id=leaderboard_id,
        model=model_name,
        created_at=created_at
    )
    
    db.add(db_round)
    db.commit()
    db.refresh(db_round)
    return db_round

def get_generation(db: Session, generation_id: int):
    return db.query(models.Generation).filter(models.Generation.id == generation_id).first()

def get_generations(db: Session, skip: int = 0, limit: int = 100, player_id: int = None, leaderboard_id: int = None, order_by: str = "id"):
    if order_by == "id":
        if leaderboard_id and player_id:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            filter(models.Round.leaderboard_id == leaderboard_id).\
            filter(models.Round.player_id == player_id).\
            order_by(models.Generation.id.desc()).offset(skip).limit(limit).all()
        elif leaderboard_id:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            filter(models.Round.leaderboard_id == leaderboard_id).\
            order_by(models.Generation.id.desc()).offset(skip).limit(limit).all()
        elif player_id:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            filter(models.Round.player_id == player_id).\
            order_by(models.Generation.id.desc()).offset(skip).limit(limit).all()
        else:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
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
            order_by(models.Generation.total_score.desc()).offset(skip).limit(limit).all()
        elif leaderboard_id:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            filter(models.Round.leaderboard_id == leaderboard_id).\
            order_by(models.Generation.total_score.desc()).offset(skip).limit(limit).all()
        elif player_id:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            filter(models.Round.player_id == player_id).\
            order_by(models.Generation.total_score.desc()).offset(skip).limit(limit).all()
        else:
            generations = db.query(
                models.Generation,
                models.Round
            ).\
            join(models.Round, models.Generation.round_id == models.Round.id).\
            order_by(models.Generation.total_score.desc()).offset(skip).limit(limit).all()
    else:
        raise ValueError("Invalid order_by value")
    return generations

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

    return db_score

def update_score(db: Session, score: schemas.ScoreUpdate):
    db_score = db.query(models.Score).filter(models.Score.id == score.id).first()
    db_score.image_similarity = score.image_similarity
    db.commit()
    db.refresh(db_score)
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

def get_leaderboard_vocabulary(db: Session, leaderboard_vocabulary_id: int):
    return db.query(models.LeaderboardVocabulary).filter(models.LeaderboardVocabulary.id == leaderboard_vocabulary_id).first()

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

