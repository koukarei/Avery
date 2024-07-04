from enum import Enum
from typing import List,Optional
from engine.function.keywords import get_ai_keywords
from sklearn.metrics.pairwise import cosine_similarity
import cv2
from sewar.full_ref import ssim
import numpy as np

class Rank(str,Enum):
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

def calulate_spelling_score(
        original_token:List[str],
        modified_token:List[str]
):
    pass


class Score():
    def __init__(self):
        self.Grammar=0
        self.Vocabulary=0
        self.ssim=0
        self.EffectiveCom=0
        self.total=0
        self.Rank=Rank.F
        self.ssims=[]

    def set_Grammar(
            self,
            original_sentence,
            modified_sentence,
            mix_level=0.5
    ):
        # number of token
        original_token=original_sentence.split()
        modified_token=modified_sentence.split()

        tokens=List(set(original_token+modified_token))

        original_arr=[]
        modified_arr=[]

        for i in tokens:
            original_arr.append(len([j for j in original_token if j==i]))
            modified_arr.append(len([j for j in modified_token if j==i]))

        num_score=cosine_similarity(original_arr,modified_arr)

        # ordering of token
        order_score=0
        for i in len(original_token):
            if original_token[i]==modified_token[i]:
                order_score+=1
        order_score/=len(original_token)
        self.Grammar=mix_level*num_score+(1-mix_level)*order_score

    def set_Vocabulary(
            self,
            used_keywords,
    ):
        '''
        For each used keyword, calculate discount based on the spelling.
        calculate the keyword score by CEFR-J <not done>
        '''
        self.Vocabulary=sum([i.discount() for i in used_keywords])
    
    def ssim_ai_behavior(
            self,
            img,
    ):
        from engine.function.keywords import get_ai_keywords
        keywords=get_ai_keywords(img)
        from engine.function.sentence import genSentences
        sentence=genSentences(keywords)
        from engine.function.gen_image import gen_image
        interpreted=gen_image(sentence)
        self.ssims.append(ssim(img,interpreted)[0])

    def set_EffectiveCom(
            self,
            original_img,
            interpreted_img,
            leaderboardId:Optional[str]=None,
    ):
        interpreted_keywords=get_ai_keywords(interpreted_img)
        original_keywords=get_ai_keywords(original_img)

        keywords=List(set(interpreted_keywords+original_keywords))

        keyword_similarity=cosine_similarity(
            [i in interpreted_keywords for i in keywords],
            [i in original_keywords for i in keywords]
        )
        original2=cv2.resize(
            original_img,
            (interpreted_img.shape[1],interpreted_img.shape[0]),
            interpolation=cv2.INTER_AREA
        )
        self.ssim=ssim(original2,interpreted_img)[0]
        if leaderboardId:
            leaderboard={"average_ssim":0.5,"std_ssim":0.1}
            avg_ssim=leaderboard["average_ssim"]
            std_ssim=leaderboard["std_ssim"]
        else:
            self.ssims.append(self.ssim)
            avg_ssim=np.average(self.ssims)
            std_ssim=np.std(self.ssims)
        
        ssim_similarity=(self.ssim-avg_ssim)/std_ssim/10+0.5

        self.EffectiveCom=0.6*keyword_similarity+0.4*ssim_similarity
        



