from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import numpy as np

class Rank(Enum):
    SSS="SSS"
    SS="SS"
    S="S"
    A="A"
    B="B"
    C="C"
    D="D"
    E="E"
    F="F"

    def obtainRank(self,score):
        if score.total>=95:
            return Rank.SSS
        elif score.total>=88:
            return Rank.SS
        elif score.total>=80:
            return Rank.S
        elif score.total>=70:
            return Rank.A
        elif score.total>=60:
            return Rank.B
        elif score.total>=50:
            return Rank.C
        elif score.total>=40:
            return Rank.D
        elif score.total>=30:
            return Rank.E
        else:
            return Rank.F
        

class Score(BaseModel):
    Grammar: int = Field(...,example=np.random.normal(loc=0.5,scale=0.1))
    Vocabulary: int = Field(...,example=np.random.normal(loc=0.5,scale=0.1))
    keyword_similarity: int = Field(...,example=np.random.normal(loc=0.5,scale=0.1))
    ssim: int = Field(...,example=np.random.normal(loc=0.5,scale=0.1))
    mix_level: int = Field(...,example=0.5)
    EffectiveCom: int = Field(...,example=keyword_similarity*mix_level+ssim*(1-mix_level))
    total: int = Field(...,example=np.average(Grammar+Vocabulary+EffectiveCom))
    rank: Rank = Field(...,example=Rank().obtainRank(total))
    ssims: Optional[list] = Field(...,example=lambda: np.array(list(map(lambda x: np.random.normal(0.5,0.1), range(3)))))


    