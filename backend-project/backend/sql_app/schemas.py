from pydantic import BaseModel

import datetime

class ImageBase(BaseModel):
    image_path: str

class OriginalImage(ImageBase):
    id: int

    class Config:
        orm_mode = True

class InterpretedImage(ImageBase):
    id: int
    round_id: int

    class Config:
        orm_mode = True

class MessageBase(BaseModel):
    content: str
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

class LeaderboardCreate(LeaderboardBase):
    scene_id: int
    story_id: int
    original_image_id: int
    created_by_id: int

class VocabularyBase(BaseModel):
    word: str
    meaning: str
    
class Vocabulary(VocabularyBase):
    id: int

    class Config:
        orm_mode = True

class Leaderboard(LeaderboardCreate):
    id: int
    original_image_id: int
    created_by: int
    vocabularies: list[Vocabulary]=[]

    class Config:
        orm_mode = True

class RoundBase(BaseModel):
    player_id: int
    leaderboard: int
    chat_history: int

class Round(RoundBase):
    id: int
    created_at: datetime.datetime

    class Config:
        orm_mode = True

class RoundSentence(Round):
    sentence: str

    class Config:
        orm_mode = True

class RoundCorrectSentence(RoundSentence):
    correct_sentence: str

    class Config:
        orm_mode = True

class RoundInterpretation(RoundCorrectSentence):
    interpreted_image_id: int

class RoundComplete(RoundInterpretation):
    grammar_score: int
    vocabulary_score: int
    effectiveness_score: int
    total_score: int
    rank: str
    duration: int
    is_completed: bool

class RoundOut(BaseModel):
    id: int
    player: UserOut
    interpreted_image: InterpretedImage
    sentence: str
    correct_sentence: str
    total_score: int
    rank: str
    duration: int

    class Config:
        orm_mode = True

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

class PersonalDictionaryBase(BaseModel):
    user_id: int
    vocabulary_id: int
    save_at_round_id: int

class PersonalDictionaryCreate(PersonalDictionaryBase):
    id: int
    created_at: datetime.datetime

    class Config:
        orm_mode = True

class PersonalDictionary(PersonalDictionaryBase):
    id: int
    created_at: datetime.datetime
    used_times: int
    position_top: int
    position_left: int
    size_width: int
    size_height: int
    note: str

    class Config:
        orm_mode = True
        
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
    story: Story
    created_by: UserOut
    vocabularies: list[Vocabulary]=[]

    class Config:
        orm_mode = True