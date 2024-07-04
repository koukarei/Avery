from sqlalchemy.orm import Session

from . import models, schemas

def get_vocabulary(db: Session, vocabulary_id: int):
    return db.query(models.Vocabulary).filter(models.Vocabulary.id == vocabulary_id).first()

def get_vocabulary_by_word(db: Session, word: str):
    def get_vocab(word:str):
        yield db.query(models.Vocabulary).filter(models.Vocabulary.word == word).first()
        yield db.query(models.Vocabulary).filter(models.Vocabulary.singular == word).first()
        yield db.query(models.Vocabulary).filter(models.Vocabulary.present_participle == word).first()
        yield db.query(models.Vocabulary).filter(models.Vocabulary.past_tense == word).first()
        yield db.query(models.Vocabulary).filter(models.Vocabulary.past_participle == word).first()
    for vocab in get_vocab(word):
        if vocab:
            return vocab
    return None

def get_vocabularies(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Vocabulary).offset(skip).limit(limit).all()

def get_vocabularies_by_rank(db: Session, rank: int, skip: int = 0, limit: int = 100):
    return db.query(models.Vocabulary).filter(models.Vocabulary.rank == rank).offset(skip).limit(limit).all()

def get_vocabularies_by_leaderboard(db: Session, leaderboard_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Vocabulary).filter(models.Vocabulary.leaderboards.any(id=leaderboard_id)).offset(skip).limit(limit).all()

def create_vocabulary(db: Session, vocabulary: schemas.VocabularyCreate):
    db_vocab = models.Vocabulary(**vocabulary.model_dump())
    db.add(db_vocab)
    db.commit()
    db.refresh(db_vocab)
    return db_vocab

def delete_vocabulary(db: Session, vocabulary_id: int):
    db.query(models.Vocabulary).filter(models.Vocabulary.id == vocabulary_id).delete()
    db.commit()

def get_personal_dictionary(db: Session, personal_dictionary_id: int):
    return db.query(models.PersonalDictionary).filter(models.PersonalDictionary.id == personal_dictionary_id).first()

def get_personal_dictionaries_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.PersonalDictionary).filter(models.PersonalDictionary.user_id == user_id).offset(skip).limit(limit).all()

def get_personal_dictionaries_by_vocabulary(db: Session, vocabulary_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.PersonalDictionary).filter(models.PersonalDictionary.vocabulary_id == vocabulary_id).offset(skip).limit(limit).all()

def get_personal_dictionaries_by_round(db: Session, round_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.PersonalDictionary).filter(models.PersonalDictionary.round_id == round_id).offset(skip).limit(limit).all()

def create_personal_dictionary(db: Session, personal_dictionary: schemas.PersonalDictionaryCreate):
    db_personal_dictionary = models.PersonalDictionary(**personal_dictionary.model_dump())
    db.add(db_personal_dictionary)
    db.commit()
    db.refresh(db_personal_dictionary)
    return db_personal_dictionary

def delete_personal_dictionary(db: Session, personal_dictionary_id: int):
    db.query(models.PersonalDictionary).filter(models.PersonalDictionary.id == personal_dictionary_id).delete()
    db.commit()

def get_scene(db: Session, scene_id: int):
    return db.query(models.Scene).filter(models.Scene.id == scene_id).first()

def get_scenes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Scene).offset(skip).limit(limit).all()

def create_scene(db: Session, scene: schemas.SceneCreate):
    db_scene = models.Scene(**scene.model_dump())
    db.add(db_scene)
    db.commit()
    db.refresh(db_scene)
    return db_scene

def delete_scene(db: Session, scene_id: int):
    db.query(models.Scene).filter(models.Scene.id == scene_id).delete()
    db.commit()

def get_leaderboard(db: Session, leaderboard_id: int):
    return db.query(models.Leaderboard).filter(models.Leaderboard.id == leaderboard_id).first()

def get_leaderboards(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Leaderboard).offset(skip).limit(limit).all()

def get_leaderboards_by_scene(db: Session, scene_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Leaderboard).filter(models.Leaderboard.scene_id == scene_id).offset(skip).limit(limit).all()

def create_leaderboard(db: Session, leaderboard: schemas.LeaderboardCreate):
    db_leaderboard = models.Leaderboard(**leaderboard.model_dump())
    db.add(db_leaderboard)
    db.commit()
    db.refresh(db_leaderboard)
    return db_leaderboard

def delete_leaderboard(db: Session, leaderboard_id: int):
    db.query(models.Leaderboard).filter(models.Leaderboard.id == leaderboard_id).delete()
    db.commit()

def get_good_round(db: Session, round_id: int):
    return db.query(models.GoodRound).filter(models.GoodRound.round_id == round_id).first()

def get_good_rounds(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.GoodRound).offset(skip).limit(limit).all()

def create_good_round(db: Session, good_round: schemas.GoodRoundCreate):
    db_good_round = models.GoodRound(**good_round.model_dump())
    db.add(db_good_round)
    db.commit()
    db.refresh(db_good_round)
    return db_good_round

def delete_good_round(db: Session, good_round_id: int):
    db.query(models.GoodRound).filter(models.GoodRound.id == good_round_id).delete()
    db.commit()

def get_round(db: Session, round_id: int):
    return db.query(models.Round).filter(models.Round.id == round_id).first()

def update_round(db: Session, round_id: int, round: schemas.RoundUpdate):
    db.query(models.Round).filter(models.Round.id == round_id).update(round.model_dump())
    db.commit()
    return db.query(models.Round).filter(models.Round.id == round_id).first()

def update_round2(db: Session, round_id: int, round: schemas.RoundUpdate2):
    db.query(models.Round).filter(models.Round.id == round_id).update(round.model_dump())
    db.commit()
    return db.query(models.Round).filter(models.Round.id == round_id).first()

def update_round3(db: Session, round_id: int, round: schemas.RoundUpdate3):
    db.query(models.Round).filter(models.Round.id == round_id).update(round.model_dump())
    db.commit()
    return db.query(models.Round).filter(models.Round.id == round_id).first()

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def get_users_by_leaderboard(db: Session, leaderboard_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.User).filter(models.User.rounds.leaderboard.id==leaderboard_id).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(email=user.email, hashed_password=user.hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

