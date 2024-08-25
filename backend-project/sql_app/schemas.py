from pydantic import BaseModel

import datetime

class ImageBase(BaseModel):
    image_path: str

class OriginalImage(ImageBase):
    id: int
    leaderboard_id: int

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

class UserProfileBase(BaseModel):
    display_name: str
    bio: str
    avatar: str
    level: int
    xp: int

class LeaderboardBase(BaseModel):
    title: str
    original_image: int
    scene: int
    story: int
    story_extract: str

class VocabularyBase(BaseModel):
    word: str
    meaning: str
    
class Vocabulary(VocabularyBase):
    id: int

    class Config:
        orm_mode = True

class Leaderboard(LeaderboardBase):
    id: int
    created_by: int
    vocabularies: list[Vocabulary]=[]

    class Config:
        orm_mode = True


class RoundBase(BaseModel):
    player_id: int
    leaderboards: int
    chat_history: int

class Round(RoundBase):
    id: int

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
    interpreted_image: int

class RoundComplete(RoundInterpretation):
    grammar_score: int
    vocabulary_score: int
    effectiveness_score: int
    total_score: int
    rank: str
    duration: int
    is_completed: bool

class UserProfile(UserProfileBase):
    id: int
    user_id: int

    rounds: list[Round]=[]

    class Config:
        orm_mode = True

class User(UserBase):
    id: int
    is_active: bool
    userprofile: UserProfile

    class Config:
        orm_mode = True

class StoryBase(BaseModel):
    title: str
    content: str
    scene_id: int

class Story(StoryBase):
    id: int

    class Config:
        orm_mode = True

class PersonalDictionaryBase(BaseModel):
    user_id: int
    vocabulary_id: int
    save_at_round: int

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

class GoodRound(BaseModel):
    player_id: int
    round_id: int