from pydantic import BaseModel, Field, field_validator

import datetime
from typing import Optional

class ImageBase(BaseModel):
    image_path: str

class OriginalImage(ImageBase):
    id: int

    class Config:
        orm_mode = True

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

class UserCreate(UserBase):
    password: str
    display_name: str

    class Config:
        orm_mode = True

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

class LeaderboardBase(BaseModel):
    title: str
    story_extract: str
    is_public: bool

class LeaderboardCreate(LeaderboardBase):
    scene_id: int
    story_id: Optional[int]
    original_image_id: int
    created_by_id: int

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
    n_words: int
    n_conjunctions: int
    n_adj: int
    n_adv: int
    n_pronouns: int
    n_prepositions: int

    n_grammar_errors: int
    n_spelling_errors: int

    perlexity: float

    f_word: float
    f_bigram: float

    n_clauses: int

    content_score: int

    total_score: int
    rank: str
    duration: int
    is_completed: bool

class GenerationOut(GenerationComplete):
    sentence: str
    correct_sentence: str
    interpreted_image: InterpretedImage

    class Config:
        orm_mode = True

class RoundComplete(BaseModel):
    id: int
    last_generation_id: int
    duration: int
    is_completed: bool

class RoundOut(BaseModel):
    id: int
    player: UserOut
    generations: list[GenerationOut]=[]

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