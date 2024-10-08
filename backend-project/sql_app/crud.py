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
    db_user = models.User(email=user.email, hashed_password=fake_hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_leaderboards(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Leaderboard).offset(skip).limit(limit).all()

def create_leaderboard(db: Session, leaderboard: schemas.LeaderboardCreate):
    db_leaderboard = models.Leaderboard(**leaderboard.dict())
    db.add(db_leaderboard)
    db.commit()
    db.refresh(db_leaderboard)
    return db_leaderboard

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