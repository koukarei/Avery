from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    display_name: str

class UserLti(BaseModel):
    user_id: int
    username: str
    display_name: str
    roles: str
    email: str
    school: str

class UserProfile(BaseModel):
    id: int
    display_name: str
    bio: str
    avatar: str

class User(BaseModel):
    id: int
    is_active: bool
    profiles: UserProfile
    username: str
    email: str
    is_admin: bool
    user_type: str

class Image(BaseModel):
    id: int
    image: str

class Vocabulary(BaseModel):
    id: int
    word: str
    meaning: str
    pos: str

class Leaderboard(BaseModel):
    id: int
    title: str
    story_extract: str
    is_public: bool
    published_at: Optional[datetime]=None
    vocabularies: list[Vocabulary]=[]

class LeaderboardDetail(BaseModel):
    id: int
    title: str
    story_extract: str
    is_public: bool
    scene_id: int
    story_id: Optional[int]
    original_image_id: int
    created_by: int=0
    vocabularies: list[Vocabulary]=[]

class MessageSend(BaseModel):
    content: str
    created_at: datetime
    is_hint: Optional[bool]=False

class MessageReceive(MessageSend):
    id: int
    sender: str

class Chat(BaseModel):
    id: int
    messages: list[MessageReceive]=[]

class GenerationCreate(BaseModel):
    round_id: int
    created_at: datetime
    generated_time: int
    sentence: str

class UserOut(BaseModel):
    id: int
    display_name: str
    level: int

class IdOnly(BaseModel):
    id: int

class Round(BaseModel):
    id: int
    player: Optional[UserOut]=None
    created_at: Optional[datetime]=None
    last_generation_id: Optional[int]=None
    chat_history: int
    generations: list[IdOnly]=[]

class RoundStart(BaseModel):
    model: Optional[str]="gpt-4o-mini"
    program: Optional[str]="none"
    leaderboard_id: int
    created_at: datetime

class RoundStartOut(BaseModel):
    id: int
    created_at: datetime
    player_id: int


class GenerationStart(BaseModel):
    round_id: int
    created_at: datetime
    generated_time: int
    sentence: str

class GenerationCorrectSentence(BaseModel):
    id: int
    correct_sentence: str

class GenerationInterpretation(BaseModel):
    id: int
    interpreted_image_id: int

class GenerationCompleteCreate(BaseModel):
    id: int
    at: datetime

class GenerationComplete(BaseModel):
    id: int
    grammar_errors: Optional[str] = None
    spelling_errors: Optional[str] = None
    evaluation_id: Optional[int] = None

    total_score: Optional[int] = None
    rank: Optional[str] = None
    duration: Optional[int] = None
    is_completed: bool

class ScoreCreate(BaseModel):
    generation_id: int
    grammar_score: float
    spelling_score: float
    vividness_score: float
    convention: bool
    structure_score: int
    content_score: int

class ScoreUpdate(BaseModel):
    id: int
    image_similarity: float

class Score(ScoreCreate):
    id: int
    image_similarity: Optional[float]=None

class GenerationOut(GenerationComplete):
    sentence: Optional[str]=None
    correct_sentence: Optional[str]=None
    interpreted_image: Optional[IdOnly]=None
    score: Optional[Score]=None

class GenerationRound(BaseModel):
    generation: GenerationOut
    round: Round

class ImageSimilarity(BaseModel):
    semantic_score_original: float
    semantic_score_interpreted: float
    blip2_score: float
    ssim: float
    similarity: float
    
class VocabularyBase(BaseModel):
    word: str
    meaning: str
    pos: str

class LeaderboardUpdate(BaseModel):
    id: int
    is_public: Optional[bool]=None
    published_at: Optional[datetime]=None
    title: Optional[str]=None
    school: list[str]=[]
    vocabularies: list[VocabularyBase]=[]

class ResponseLeaderboard(BaseModel):
    id: int
    image: str

class ResponseRound(BaseModel):
    id: int
    generated_time: int
    generations: Optional[list[int]]=[]

class ResponseGeneration(BaseModel):
    id: int
    interpreted_image: Optional[str]=None
    evaluation_msg: Optional[str]=None
    generated_time: Optional[int]=None
    sentence: Optional[str]=None
    correct_sentence: Optional[str]=None
    is_completed: Optional[bool]=None
    image_similarity: Optional[float]=None

class Response(BaseModel):
    feedback: Optional[str]=None
    leaderboard: Optional[ResponseLeaderboard]=None
    round: Optional[ResponseRound]=None
    chat: Optional[Chat]=None
    generation: Optional[ResponseGeneration]=None