from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, TEXT, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import MEDIUMTEXT, LONGTEXT

import datetime

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    lti = Column(Boolean, default=False)
    lti_user_id = Column(Integer, nullable=True)
    lti_username = Column(String(100), nullable=True)
    school = Column(String(100), nullable=True)
    email = Column(String(255), index=True)
    username = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    profile_id = Column(Integer, ForeignKey("user_profiles.id"))
    user_type = Column(String(25), default='student')

    profiles = relationship("UserProfile", back_populates="user")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    display_name = Column(String(100), index=True)
    bio = Column(String(255))
    avatar = Column(String(255))
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)

    user = relationship("User", back_populates="profiles")

    leaderboards = relationship("Leaderboard", back_populates="created_by")
    rounds = relationship("Round", back_populates="player")

class Scene(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), index=True)
    prompt = Column(String(255), index=True)

    stories = relationship("Story", back_populates="scene")
    leaderboards = relationship("Leaderboard", back_populates="scene")

class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), index=True)
    content = Column(LONGTEXT)
    scene_id=Column(Integer,ForeignKey("scenes.id"))
    
    scene = relationship("Scene", back_populates="stories")

    vocabularies = relationship("Vocabulary",secondary="story_vocabulary", back_populates="stories")
    leaderboards = relationship("Leaderboard", back_populates="story")

class Leaderboard(Base):
    __tablename__ = "leaderboards"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), index=True)
    is_public = Column(Boolean, default=True)
    original_image_id=Column(Integer,ForeignKey("original_images.id"))
    scene_id=Column(Integer,ForeignKey("scenes.id"))
    story_id=Column(Integer,ForeignKey("stories.id"),nullable=True)
    story_extract=Column(String(255), index=True)
    published_at = Column(DateTime, default=datetime.datetime.now())
    difficulty = Column(Integer, default=1)
    response_id = Column(String(100), nullable=True)

    created_by_id = Column(Integer, ForeignKey("user_profiles.id"))
    created_by = relationship("UserProfile", back_populates="leaderboards")

    original_image = relationship("OriginalImage", back_populates="leaderboard",foreign_keys=[original_image_id])
    scene = relationship("Scene", back_populates="leaderboards",foreign_keys=[scene_id])
    story = relationship("Story", back_populates="leaderboards",foreign_keys=[story_id])
    vocabularies = relationship("Vocabulary",secondary="leaderboard_vocabulary", back_populates="leaderboards")

    rounds = relationship("Round", back_populates="leaderboard")
    descriptions = relationship("Description", back_populates="leaderboard")

class Description(Base):
    __tablename__ = "descriptions"

    id = Column(Integer, primary_key=True)
    content = Column(String(255), index=True)
    model = Column(String(100), index=True)

    leaderboard_id=Column(Integer,ForeignKey("leaderboards.id"))
    leaderboard = relationship("Leaderboard", back_populates="descriptions")

class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), index=True)
    description = Column(String(255), index=True)
    feedback = Column(String(100), index=True)

    rounds = relationship("Round", back_populates="program")

class Round(Base): 
    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True)
    chat_history=Column(Integer,ForeignKey("chats.id"))
    leaderboard_id=Column(Integer,ForeignKey("leaderboards.id"))
    player_id = Column(Integer, ForeignKey("user_profiles.id"))
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=True)

    model=Column(String(100), index=True)

    created_at = Column(DateTime, default=datetime.datetime.now())
    duration = Column(Integer, default=0,nullable=True)
    last_generation_id = Column(Integer, nullable=True)

    is_completed = Column(Boolean, default=False)
    
    program = relationship("Program", back_populates="rounds")
    player = relationship("UserProfile", back_populates="rounds",foreign_keys=[player_id])
    personal_dictionaries = relationship("PersonalDictionary", back_populates="save_at_round")
    generations = relationship("Generation", back_populates="round")
    leaderboard = relationship("Leaderboard", back_populates="rounds", foreign_keys=[leaderboard_id])
    chat = relationship("Chat", foreign_keys=[chat_history])

class Generation(Base): 
    __tablename__ = "generations"

    id = Column(Integer, primary_key=True)

    sentence = Column(MEDIUMTEXT, nullable=True)
    correct_sentence = Column(MEDIUMTEXT, nullable=True)

    grammar_errors = Column(MEDIUMTEXT, nullable=True)
    spelling_errors = Column(MEDIUMTEXT, nullable=True)

    total_score = Column(Integer, default=0,nullable=True)
    rank = Column(String(1), default='F',nullable=True)
    generated_time = Column(Integer, default=1,nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.now())
    duration = Column(Integer, default=0,nullable=True)

    is_completed = Column(Boolean, default=False)
    
    interpreted_image_id=Column(Integer,ForeignKey("interpreted_images.id"),nullable=True)
    round_id=Column(Integer,ForeignKey("rounds.id"))
    score_id=Column(Integer,ForeignKey("scores.id"),nullable=True)
    evaluation_id = Column(Integer, ForeignKey("messages.id"), nullable=True)

    interpreted_image = relationship("InterpretedImage", back_populates="generation",foreign_keys=[interpreted_image_id])
    round = relationship("Round", back_populates="generations",foreign_keys=[round_id])
    score = relationship("Score",foreign_keys=[score_id])
    evaluation = relationship("Message", foreign_keys=[evaluation_id])

class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True)
    grammar_score = Column(Float(precision=10), default=0)
    spelling_score = Column(Float(precision=10), default=0)
    vividness_score = Column(Float(precision=10), default=0)
    convention = Column(Boolean, default=False)
    structure_score = Column(Integer, default=0)
    content_score = Column(Integer, default=0)
    image_similarity = Column(Float(precision=10), default=0, nullable=True)

    generation_id = Column(Integer, ForeignKey("generations.id"))

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True)
    messages = relationship("Message", back_populates="chat")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    response_id = Column(String(100), nullable=True)
    content = Column(MEDIUMTEXT)
    sender = Column(String(50), index=True)
    created_at = Column(DateTime, default=datetime.datetime.now())
    is_hint = Column(Boolean, default=False)
    is_evaluation = Column(Boolean, default=False)

    chat = relationship("Chat", back_populates="messages")

class Vocabulary(Base):
    __tablename__ = "vocabularies"

    id = Column(Integer, primary_key=True)
    word = Column(String(255), index=True)
    pos = Column(String(50), index=True) # Part of Speech
    meaning = Column(MEDIUMTEXT)

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
    save_at_round_id = Column(Integer, ForeignKey("rounds.id"))

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
    image = Column(MEDIUMTEXT)

    leaderboard = relationship("Leaderboard", back_populates="original_image")
    
class InterpretedImage(Base):
    __tablename__ = "interpreted_images"

    id = Column(Integer, primary_key=True)
    image = Column(MEDIUMTEXT)

    generation = relationship("Generation", back_populates="interpreted_image")

class GoodOriginal(Base):
    __tablename__ = "good_originals"

    player = Column(Integer, ForeignKey("users.id"),primary_key=True)
    original = Column(Integer, ForeignKey("original_images.id"),primary_key=True)

class GoodInterpreted(Base):
    __tablename__ = "good_interpreteds"

    player = Column(Integer, ForeignKey("users.id"),primary_key=True)
    interpreted = Column(Integer, ForeignKey("interpreted_images.id"),primary_key=True)

class GoodRound(Base):
    __tablename__ = "good_rounds"

    player = Column(Integer, ForeignKey("users.id"),primary_key=True)
    round = Column(Integer, ForeignKey("rounds.id"),primary_key=True)

class School_Leaderboard(Base):
    __tablename__ = "school_leaderboards"

    id = Column(Integer, primary_key=True)
    school = Column(String(100))
    leaderboard_id = Column(Integer, ForeignKey("leaderboards.id"))

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(100), primary_key=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=True)
    
    leaderboard_id = Column(Integer, ForeignKey("leaderboards.id"), nullable=True)

class User_Action(Base):
    __tablename__ = "user_actions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100))
    sent_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, default=datetime.datetime.now())
    responded_at = Column(DateTime, nullable=True)