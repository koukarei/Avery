from pydantic import BaseModel
from datetime import datetime


class VocabularyBase(BaseModel):
    word: str
    word_class: str
    definition: str
    rank: int
    singular: str|None = None
    present_participle: str|None = None
    past_tense: str|None = None
    past_participle: str|None = None

class VocabularyCreate(VocabularyBase):
    pass

class Vocabulary(VocabularyBase):
    id: int
    leaderboards: list["Leaderboard"] = []

    class Config:
        orm_mode = True
    
class PersonalDictionaryBase(BaseModel):
    user_id: int
    round_id: int
    vocabulary_id: int
    image_path: str
    image_height: int
    image_width: int
    image_top: int
    image_left: int
    recent_wrong_spelling: str|None = None
    note: str|None = None

class PersonalDictionaryCreate(PersonalDictionaryBase):
    pass

class PersonalDictionary(PersonalDictionaryBase):
    id: int
    created_at: datetime
    used_times: int
    vocabulary: Vocabulary
    user: "User"

    class Config:
        orm_mode = True

class RoundBase(BaseModel):
    leaderboard_id: int
    player_id: int
    image_path: str

class RoundCreate(RoundBase):
    pass

class RoundUpdate(RoundBase):
    keywords: list[Vocabulary]

class RoundUpdate2(RoundUpdate):
    sentence: str
    corrected_sentence: str
    image_path: str

class RoundUpdate3(RoundUpdate2):
    keyword_similarity_score: float
    ssim: float
    vocabulary_score: float
    grammar_score: float
    scoring: int

class Round(RoundUpdate3):
    id: int
    is_draft: bool = True

    player: "User"
    leaderboard: "Leaderboard"
    keywords: list[Vocabulary] = []

    class Config:
        orm_mode = True

class UserBase(BaseModel):
    username: str
    email: str
    display_name: str
    hashed_password: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    level: int
    is_active: bool
    rounds: list[Round] = []
    personal_dictionaries: list[PersonalDictionary] = []

    class Config:
        orm_mode = True

class GoodRoundBase(BaseModel):
    id: int
    round_id: int

class GoodRoundCreate(GoodRoundBase):
    pass

class GoodRound(GoodRoundBase):
    round: Round

    class Config:
        orm_mode = True


class PersonalDictionaryBase(BaseModel):
    id: int
    user_id: int
    vocabulary_id: int
    image_path: str
    image_height: int
    image_width: int
    image_top: int
    image_left: int
    recent_wrong_spelling: str|None = None
    note: str|None = None

class PersonalDictionaryCreate(PersonalDictionaryBase):
    pass

class LeaderboardBase(BaseModel):
    scene_id: int
    image_path: str

    ai_keywords: list[Vocabulary] = []

class LeaderboardCreate(LeaderboardBase):
    pass

class Leaderboard(LeaderboardBase):
    id: int
    popular_keywords: list[Vocabulary] = []
    scene: "Scene"

    class Config:
        orm_mode = True

class SceneBase(BaseModel):
    name: str
    prompt: str

class SceneCreate(SceneBase):
    pass

class Scene(SceneBase):
    id: int
    leaderboards: list[Leaderboard] = []

    class Config:
        orm_mode = True

