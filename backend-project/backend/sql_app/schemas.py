from pydantic import BaseModel, Field, field_validator

import datetime
from typing import Optional

class ImageBase(BaseModel):
    image_path: str

class OriginalImage(ImageBase):
    id: int

    class Config:
        orm_mode = True

class IdOnly(BaseModel):
    id: int

class InterpretedImage(ImageBase):
    id: int

    class Config:
        orm_mode = True

class InterpretedImageOut(ImageBase):
    id: int

    class Config:
        orm_mode = True

class MessageReceive(BaseModel):
    content: str
    created_at: datetime.datetime

class MessageBase(MessageReceive):
    sender: str

class Message(MessageBase):
    id: int

class ChatBase(BaseModel):
    messages: list[Message]=[]

class Chat(ChatBase):
    id: int

    class Config:
        orm_mode = True

class SceneBase(BaseModel):
    name: str
    prompt: str

class Scene(SceneBase):
    id: int

    class Config:
        orm_mode = True

class UserBase(BaseModel):
    username: str
    email: str
    is_admin: Optional[bool] = False
    user_type: Optional[str] = "student"

class UserCreate(UserBase):
    password: str
    display_name: str

    class Config:
        orm_mode = True

class UserCreateLti(UserBase):
    user_id: int
    username: str
    display_name: str
    roles: str
    email: str
    school: str

class UserProfileBase(BaseModel):
    display_name: str
    bio: str
    avatar: str

class UserProfileOut(BaseModel):
    display_name: str
    level:int

class UserExp(BaseModel):
    level: int
    xp: int

class UserOut(BaseModel):
    id: int
    display_name: str
    level: int

class UserUpdateIn(BaseModel):
    username: Optional[str]
    email: Optional[str]
    id: Optional[int]
    is_admin: Optional[bool]
    is_active: Optional[bool]
    user_type: Optional[str]

class UserUpdate(BaseModel):
    id: int
    is_admin: Optional[bool]
    is_active: Optional[bool]
    user_type: Optional[str]

class LeaderboardBase(BaseModel):
    title: str
    story_extract: str
    is_public: bool

class LeaderboardCreateIn(LeaderboardBase):
    scene_id: int
    story_id: Optional[int]
    original_image_id: int

class LeaderboardCreate(LeaderboardCreateIn):
    created_by_id: int=0

class VocabularyBase(BaseModel):
    word: str
    meaning: str
    pos: str
    
class Vocabulary(VocabularyBase):
    id: int

    class Config:
        orm_mode = True

class Leaderboard(LeaderboardCreate):
    id: int
    original_image_id: int
    created_by_id: int
    vocabularies: list[Vocabulary]=[]

    class Config:
        orm_mode = True

class RoundCreate(BaseModel):
    leaderboard_id: int
    model: str="gpt-4o-mini"
    created_at: datetime.datetime

class RoundBase(BaseModel):
    player_id: int
    leaderboard: Leaderboard
    chat_history: int

class Round(RoundBase):
    id: int
    created_at: datetime.datetime

    class Config:
        orm_mode = True

class GenerationCreate(BaseModel):
    round_id: int
    created_at: datetime.datetime
    generated_time: int
    sentence: str

class GenerationBase(BaseModel):
    id: int
    sentence: str

    class Config:
        orm_mode = True

class GenerationCorrectSentence(BaseModel):
    id: int
    correct_sentence: str

    class Config:
        orm_mode = True

class GenerationInterpretation(BaseModel):
    id: int
    interpreted_image_id: int

class GenerationCompleteCreate(BaseModel):
    id: int
    at: datetime.datetime

class GenerationComplete(BaseModel):
    id: int
    n_words: Optional[int] = None
    n_conjunctions: Optional[int] = None
    n_adj: Optional[int] = None
    n_adv: Optional[int] = None
    n_pronouns: Optional[int] = None
    n_prepositions: Optional[int] = None

    n_grammar_errors: Optional[int] = None
    n_spelling_errors: Optional[int] = None

    perplexity: Optional[float] = None

    f_word: Optional[float] = None
    f_bigram: Optional[float] = None

    n_clauses: Optional[int] = None

    content_score: Optional[int] = None

    total_score: Optional[int] = None
    rank: Optional[str] = None
    duration: Optional[int] = None
    is_completed: bool

class GenerationOut(GenerationComplete):
    sentence: Optional[str] = None
    correct_sentence: Optional[str] = None
    interpreted_image: Optional[InterpretedImage]=None

    class Config:
        orm_mode = True

class GenerationScore(BaseModel):
    id: int
    sentence: str
    grammar_score: float
    spelling_score: float
    vividness_score: float
    convention: float
    structure_score: int
    content_score: int
    total_score: int
    rank: str

class RoundComplete(BaseModel):
    id: int
    last_generation_id: int
    duration: int
    is_completed: bool

class RoundOut(BaseModel):
    id: int
    player: UserOut
    last_generation_id: Optional[int]=None
    chat_history: int
    generations: list[IdOnly]=[]

    class Config:
        orm_mode = True

class Round_id(BaseModel):
    id: int

class UserProfile(UserProfileBase):
    id: int

    rounds: list[Round]=[]

    class Config:
        orm_mode = True

class User(UserBase):
    id: int
    is_active: bool
    profiles: UserProfile

    class Config:
        orm_mode = True

class StoryBase(BaseModel):
    title: str
    scene_id: int

class StoryCreate(StoryBase):
    textfile_path: str

class Story(StoryBase):
    id: int
    textfile_path: str

    class Config:
        orm_mode = True

class StoryOut(BaseModel):
    id: int
    title: str
    scene: Scene
    textfile_path: str

    class Config:
        orm_mode = True

class PersonalDictionaryId(BaseModel):
    player: int
    vocabulary: int

class PersonalDictionaryCreate(BaseModel):
    user_id: int
    vocabulary: str
    save_at_round_id: int
    created_at: datetime.datetime
    relevant_sentence: str

    class Config:
        orm_mode = True

class PersonalDictionaryBase(PersonalDictionaryId):
    save_at_round_id: int

class PersonalDictionary(PersonalDictionaryBase):
    created_at: datetime.datetime
    used_times: int
    position_top: int
    position_left: int
    size_width: int
    size_height: int
    note: str

    class Config:
        orm_mode = True
        
class PersonalDictionaryUpdate(PersonalDictionaryId):
    position_top: Optional[int]
    position_left: Optional[int]
    size_width: Optional[int]
    size_height: Optional[int]
    note: Optional[str]

class GoodImage(BaseModel):
    player_id: int
    image_id: int

class GoodOriginal(BaseModel):
    player: int
    original: int

class GoodInterpreted(BaseModel):
    player: int
    interpreted: int

class GoodRound(BaseModel):
    player_id: int
    round_id: int


class LeaderboardOut(LeaderboardBase):
    id: int
    original_image: OriginalImage
    scene: Scene
    story: Optional[Story]
    created_by: UserOut
    vocabularies: list[Vocabulary]=[]

    class Config:
        orm_mode = True

class DescriptionBase(BaseModel):
    content: str
    model: str
    leaderboard_id: int

class Description(DescriptionBase):
    id: int

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ImageSimilarity(BaseModel):
    semantic_score_original: float
    semantic_score_interpreted: float
    blip2_score: float

class LeaderboardPlayable(BaseModel):
    id: int
    is_playable: bool
