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

class UserCreateLti(BaseModel):
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
    image_path: str

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
    player: UserOut
    last_generation_id: Optional[int]=None
    chat_history: int
    generations: list[IdOnly]=[]

class RoundStart(BaseModel):
    model: Optional[str]="gpt-4o-mini"
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
    n_words: int
    n_conjunctions: int
    n_adj: int
    n_adv: int
    n_pronouns: int
    n_prepositions: int

    n_grammar_errors: int
    n_spelling_errors: int

    perplexity: float

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
    interpreted_image: Image

class GenerationRound(BaseModel):
    generation: GenerationOut
    round: Round