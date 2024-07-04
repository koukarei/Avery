from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, DateTime, Float
from sqlalchemy.orm import relationship

from .database import Base

leaderboard_keywords = Table('leaderboard_keywords', Base.metadata,
    Column('leaderboard_id', ForeignKey('leaderboards.id'), primary_key=True),
    Column('keyword_id', ForeignKey('vocabularies.id'), primary_key=True)
)

leaderboard_ai_keywords=Table('leaderboard_ai_keywords', Base.metadata,
    Column('leaderboard_id', ForeignKey('leaderboards.id'), primary_key=True),
    Column('keyword_id', ForeignKey('vocabularies.id'), primary_key=True)
)

round_keywords=Table('round_keywords', Base.metadata,
    Column('round_id', ForeignKey('rounds.id'), primary_key=True),
    Column('keyword_id', ForeignKey('vocabularies.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    display_name = Column(String, index=True)
    hashed_password = Column(String)
    level=Column(Integer, index=True)
    is_active = Column(Boolean, default=True)

    rounds = relationship("Round", back_populates="player")
    personal_dictionaries = relationship("Personal_Dictionary", back_populates="user")

class Vocabulary(Base):
    __tablename__ = "vocabularies"

    id = Column(Integer, primary_key=True)
    word = Column(String, index=True)
    word_class = Column(String, index=True)
    singular = Column(String, index=True)
    present_participle = Column(String, index=True)
    past_tense = Column(String, index=True)
    past_participle = Column(String, index=True)
    definition = Column(String, index=True)
    rank = Column(Integer, index=True)

    leaderboards = relationship("Leaderboard", secondary=leaderboard_keywords, back_populates="popular_keywords")

class Personal_Dictionary(Base):
    __tablename__ = "personal_dictionaries"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    round_id = Column(Integer, ForeignKey("rounds.id"))
    vocabulary_id = Column(Integer, ForeignKey("vocabularies.id"))
    created_at = Column(DateTime, index=True)
    used_times=Column(Integer, index=True) # shown as a experience bar in the front end, max experience is different for each word rank
    image_path = Column(String, index=True)
    image_height = Column(Integer, index=True)
    image_width = Column(Integer, index=True)
    image_top = Column(Integer, index=True)
    image_left = Column(Integer, index=True)
    recent_wrong_spelling=Column(String, index=True)
    note=Column(String, index=True)

    user = relationship("User", back_populates="personal_dictionaries")
    vocabulary = relationship("Vocabulary", back_populates="personal_dictionaries")
    round = relationship("Round", back_populates="personal_dictionaries")
    
class Scene(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    prompt = Column(String, index=True)

    leaderboards = relationship("Leaderboard", back_populates="scene")

class Leaderboard(Base):
    __tablename__ = "leaderboards"

    id = Column(Integer, primary_key=True)
    image_path = Column(String, index=True)
    scene_id=Column(Integer, ForeignKey("scenes.id"))
    
    popular_keywords = relationship("Vocabulary",secondary=leaderboard_keywords, back_populates="leaderboards")
    ai_keywords = relationship("Vocabulary", secondary=leaderboard_ai_keywords, back_populates="leaderboards")
    scene = relationship("Scene", back_populates="leaderboards")

class GoodRound(Base):
    __tablename__ = "good_rounds"

    id = Column(Integer, primary_key=True)
    round_id = Column(Integer, ForeignKey("rounds.id"))

    round = relationship("Round", back_populates="good_rounds")

class Round(Base):
    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True)
    sentence = Column(String, index=True)
    corrected_sentence = Column(String, index=True)
    image_path = Column(String, index=True)
    keyword_similarity_score=Column(Float, index=True)
    ssim=Column(Float, index=True)
    vocabulary_score=Column(Float, index=True)
    grammar_score=Column(Float, index=True)
    scoring=Column(Integer, index=True)
    player_id = Column(Integer, ForeignKey("users.id"))
    leaderboard_id = Column(Integer, ForeignKey("leaderboards.id"))
    is_draft = Column(Boolean, default=True)

    player = relationship("User", back_populates="rounds")
    leaderboard = relationship("Leaderboard", back_populates="rounds")
    keywords = relationship("Vocabulary", secondary=round_keywords, back_populates="rounds")