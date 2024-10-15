from sqlalchemy.orm import Session

from . import models, schemas

from typing import Union


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

def get_leaderboards(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Leaderboard).offset(skip).limit(limit).all()

def get_leaderboard(db: Session, leaderboard_id: int):
    return db.query(models.Leaderboard).filter(models.Leaderboard.id == leaderboard_id).first()

def create_leaderboard(
        db: Session, 
        leaderboard: schemas.LeaderboardCreate,
):
    db_leaderboard = models.Leaderboard(
        **leaderboard.dict()
    )

    db.add(db_leaderboard)
    db.commit()
    db.refresh(db_leaderboard)
    return db_leaderboard

def get_original_image(db: Session, image_id: int):
    return db.query(models.OriginalImage).filter(models.OriginalImage.id == image_id).first()

def create_original_image(db: Session, image: schemas.ImageBase):
    db_image = models.OriginalImage(**image.dict())
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image

def get_interpreted_image(db: Session, image_id: int):
    return db.query(models.InterpretedImage).filter(models.InterpretedImage.id == image_id).first()

def create_interpreted_image(db: Session, image: schemas.ImageBase):
    db_image = models.InterpretedImage(**image.dict())
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
        **story.dict()
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
    db_scene = models.Scene(**scene.dict())
    db.add(db_scene)
    db.commit()
    db.refresh(db_scene)
    return db_scene

def get_round(db: Session, round_id: int):
    return db.query(models.Round).filter(models.Round.id == round_id).first()

def get_rounds(db: Session, skip: int = 0, limit: int = 100, is_completed: bool = True, leaderboard_id: int = None):
    if leaderboard_id:
        return db.query(models.Round).filter(models.Round.is_completed == is_completed).filter(models.Round.leaderboard == leaderboard_id).offset(skip).limit(limit).all()
    else:
        return db.query(models.Round).filter(models.Round.is_completed == is_completed).offset(skip).limit(limit).all()

def create_round(db: Session, leaderboard_id:int, user_id: int):
    db_chat=models.Chat()
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)

    db_round = models.Round(
        player_id=user_id,
        chat_history=db_chat.id,
        leaderboards_id=leaderboard_id
    )

    db.add(db_round)
    db.commit()
    db.refresh(db_round)
    return db_round

def update_round1(db: Session, round_id: int, round: schemas.RoundSentence):
    db_round = db.query(models.Round).filter(models.Round.id == round_id).first()
    db_round.sentence = round.sentence
    db.commit()
    db.refresh(db_round)
    return db_round

def update_round2(db: Session, round_id: int, round: schemas.RoundCorrectSentence):
    db_round = db.query(models.Round).filter(models.Round.id == round_id).first()
    db_round.correct_sentence = round.correct_sentence
    db.commit()
    db.refresh(db_round)
    return db_round

def update_round3(db: Session, round_id: int, round: schemas.RoundInterpretation):
    db_round = db.query(models.Round).filter(models.Round.id == round_id).first()
    db_round.interpreted_image_id = round.interpreted_image_id
    db.commit()
    db.refresh(db_round)
    return db_round

def update_round4(db: Session, round_id: int, round: schemas.RoundComplete):
    db_round = db.query(models.Round).filter(models.Round.id == round_id).first()
    db_round.grammar_score = round.grammar_score
    db_round.vocabulary_score = round.vocabulary_score
    db_round.effectiveness_score = round.effectiveness_score
    db_round.total_score = round.total_score
    db_round.rank = round.rank
    db_round.duration = round.duration
    db_round.is_completed = round.is_completed
    db.commit()
    db.refresh(db_round)
    return db_round

def get_chat(db: Session, chat_id: int):
    return db.query(models.Chat).filter(models.Chat.id == chat_id).first()

def create_message(db: Session, message: schemas.MessageBase, chat_id: int):
    db_message = models.Message(
        chat_id=chat_id,
        **message.dict()
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)

    db_chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    db_chat.messages.append(db_message)
    db.commit()
    db.refresh(db_chat)
    return db_message

def get_vocabulary(db: Session, vocabulary_id: int):
    return db.query(models.Vocabulary).filter(models.Vocabulary.id == vocabulary_id).first()

def create_vocabulary(db: Session, vocabulary: schemas.VocabularyBase):
    db_vocabulary = models.Vocabulary(**vocabulary.dict())
    db.add(db_vocabulary)
    db.commit()
    db.refresh(db_vocabulary)
    return db_vocabulary

def get_personal_dictionary(db: Session, dictionary_id: int):
    return db.query(models.PersonalDictionary).filter(models.PersonalDictionary.id == dictionary_id).first()

def create_personal_dictionary(
        db: Session, 
        user_id: int,
        vocabulary_id: int,
        round_id: int
):
    db_dictionary = models.PersonalDictionary(
        player_id=user_id,
        vocabulary_id=vocabulary_id,
        save_at_round_id=round_id
    )

    db.add(db_dictionary)
    db.commit()
    db.refresh(db_dictionary)
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
