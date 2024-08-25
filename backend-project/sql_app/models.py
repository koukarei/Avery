from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, TEXT
from sqlalchemy.orm import relationship

import datetime

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True)
    username = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)

    profiles = relationship("UserProfile", back_populates="user")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, ForeignKey("users.id"),primary_key=True)
    display_name = Column(String(100), index=True)
    bio = Column(String(255))
    avatar = Column(String(255))
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)

    user = relationship("User", back_populates="profiles")

    rounds = relationship("Round", back_populates="player")

class Scene(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), index=True)
    prompt = Column(String(255), index=True)

    leaderboards = relationship("Leaderboard", back_populates="scene")

class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), index=True)
    content = Column(TEXT(65535), index=True)
    scene=Column(Integer,ForeignKey("scenes.id"))
    
    vocabularies = relationship("Vocabulary",secondary="story_vocabulary", back_populates="stories")
    leaderboards = relationship("Leaderboard", back_populates="story")

class Leaderboard(Base):
    __tablename__ = "leaderboards"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), index=True)
    original_image_id=Column(Integer,ForeignKey("original_images.id"))
    scene_id=Column(Integer,ForeignKey("scenes.id"))
    story_id=Column(Integer,ForeignKey("stories.id"))
    story_extract=Column(String(255), index=True)

    created_by = Column(Integer, ForeignKey("users.id"))

    original_image = relationship("OriginalImage", back_populates="leaderboard",foreign_keys=[original_image_id])
    scene = relationship("Scene", back_populates="leaderboards",foreign_keys=[scene_id])
    story = relationship("Story", back_populates="leaderboards",foreign_keys=[story_id])
    vocabularies = relationship("Vocabulary",secondary="leaderboard_vocabulary", back_populates="leaderboards")

class Round(Base): 
    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True)
    chat_history=Column(Integer,ForeignKey("chats.id"))
    leaderboard=Column(Integer,ForeignKey("leaderboards.id"))
    player_id = Column(Integer, ForeignKey("user_profiles.id"))

    sentence = Column(String(120), index=True,nullable=True)
    correct_sentence = Column(String(120), index=True,nullable=True)

    grammar_score = Column(Integer, default=0,nullable=True)
    vocabulary_score = Column(Integer, default=0,nullable=True)
    effectiveness_score = Column(Integer, default=0,nullable=True)
    total_score = Column(Integer, default=0,nullable=True)
    rank = Column(String(1), default='F',nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.now())
    duration = Column(Integer, default=0,nullable=True)

    is_completed = Column(Boolean, default=False)
    
    interpreted_image_id=Column(Integer,ForeignKey("interpreted_images.id"),nullable=True)

    interpreted_image = relationship("InterpretedImage", back_populates="round",foreign_keys=[interpreted_image_id])
    player = relationship("UserProfile", back_populates="rounds",foreign_keys=[player_id])
    personal_dictionaries = relationship("PersonalDictionary", back_populates="save_at_round")

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True)
    messages = relationship("Message", back_populates="chat")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    content = Column(TEXT(1023), index=True)
    sender = Column(String(50), index=True)

    chat = relationship("Chat", back_populates="messages")

class Vocabulary(Base):
    __tablename__ = "vocabularies"

    id = Column(Integer, primary_key=True)
    word = Column(String(255), index=True)
    meaning = Column(String(255), index=True)

    leaderboards = relationship("Leaderboard",secondary="leaderboard_vocabulary", back_populates="vocabularies")
    stories = relationship("Story",secondary="story_vocabulary", back_populates="vocabularies")

class LeaderboardVocabulary(Base):
    __tablename__ = "leaderboard_vocabulary"

    leaderboard_id = Column(Integer, ForeignKey("leaderboards.id"),primary_key=True)
    vocabulary_id = Column(Integer, ForeignKey("vocabularies.id"),primary_key=True)

class StoryVocabulary(Base):
    __tablename__ = "story_vocabulary"

    story_id = Column(Integer, ForeignKey("stories.id"),primary_key=True)
    vocabulary_id = Column(Integer, ForeignKey("vocabularies.id"),primary_key=True)

class PersonalDictionary(Base):
    __tablename__ = "personal_dictionaries"

    player = Column(Integer, ForeignKey("users.id"),primary_key=True)
    vocabulary = Column(Integer, ForeignKey("vocabularies.id"),primary_key=True)

    created_at = Column(DateTime, default=datetime.datetime.now())
    used_times = Column(Integer, default=0)
    position_top = Column(Integer, default=0)
    position_left = Column(Integer, default=0)
    size_width = Column(Integer, default=0)
    size_height = Column(Integer, default=0)
    save_at_round_id = Column(Integer, ForeignKey("rounds.id"))
    note = Column(String(512), index=True)

    save_at_round=relationship("Round", back_populates="personal_dictionaries")

class OriginalImage(Base):
    __tablename__ = "original_images"

    id = Column(Integer, primary_key=True)
    image_path = Column(String(255), index=True)

    leaderboard = relationship("Leaderboard", back_populates="original_image")

class InterpretedImage(Base):
    __tablename__ = "interpreted_images"

    id = Column(Integer, primary_key=True)
    image_path = Column(String(255), index=True)

    round = relationship("Round", back_populates="interpreted_image")

class GoodImage(Base):
    __tablename__ = "good_images"

    player = Column(Integer, ForeignKey("users.id"),primary_key=True)
    image = Column(Integer, ForeignKey("images.id"),primary_key=True)

class GoodRound(Base):
    __tablename__ = "good_rounds"

    player = Column(Integer, ForeignKey("users.id"),primary_key=True)
    round = Column(Integer, ForeignKey("rounds.id"),primary_key=True)