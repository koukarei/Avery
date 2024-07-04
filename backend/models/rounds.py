from pydantic import BaseModel,Field
from typing import Optional, List, Literal, Union, Any
from enum import Enum
from models.scores import Score

class Keyword(BaseModel):
    original: str
    spell_checked: str
    source: Literal["AI", "User"]

class Round(BaseModel):
    leaderboardId: Optional[str]=Field(...)
    id: str
    original_picture: Optional[Any]
    keywords: List[Keyword]
    sentence: Optional[str]
    score: Score
    is_draft: bool=True
    corrected_sentence: Optional[str]
    interpreted_image: Optional[Any]