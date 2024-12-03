from sqlalchemy.orm import Session

from . import models, schemas

from typing import Union
import datetime

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    fake_hashed_password = user.password + "notreallyhashed"

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
        hashed_password=fake_hashed_password,
        is_active=True,
        profile_id=db_userprofile.id
    )

    db.add(db_user)
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

def get_leaderboards(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Leaderboard).offset(skip).limit(limit).all()

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

def get_scene(db: Session, scene_id: int):
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
        return db.query(models.Round).filter(models.Round.is_completed == is_completed).filter(models.Round.leaderboard_id == leaderboard_id).filter(models.Round.player_id==player_id).offset(skip).limit(limit).all()
    elif leaderboard_id:
        return db.query(models.Round).filter(models.Round.is_completed == is_completed).filter(models.Round.leaderboard_id == leaderboard_id).offset(skip).limit(limit).all()
    elif player_id:
        return db.query(models.Round).filter(models.Round.is_completed == is_completed).filter(models.Round.player_id==player_id).offset(skip).limit(limit).all()
    else:
        return db.query(models.Round).filter(models.Round.is_completed == is_completed).offset(skip).limit(limit).all()

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

def get_vocabulary(db: Session, vocabulary: str, part_of_speech: str):
    return db.query(models.Vocabulary).filter(models.Vocabulary.word == vocabulary).filter(models.Vocabulary.pos == part_of_speech).first()

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

