from typing import List,Literal,Union
from enum import Enum

from ftlangdetect import detect
from profanity_check import predict, predict_prob
from sklearn.metrics.pairwise import cosine_similarity
import time
import uuid
import base64

from engine.models.score import Score
from engine.function.sentence import checkSentence
from engine.function.gen_image import gen_image

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

class Keyword():

    def __init__(self,original:str,spell_checked:str,source:Literal["AI","User"]):
        self.original=original
        self.spell_checked=spell_checked
        self.source=source

    def discount(self):
        if self.source=="AI":
            return 0.5
        elif self.original==self.spell_checked:
            return 1
        else:
            return 0.75


class Round():

    def __init__(self,leaderboardId:Union[str,None]=None):
        timestamp = str(int(time.time()))
        unique_id = uuid.uuid4().hex
        self.id=f"ID-{timestamp}-{unique_id}"
        self.leaderboardId=leaderboardId
        self.original_picture=None
        self.keywords=List[Keyword]
        self.sentence=None
        self.score=Score()
        self.is_draft=True

    def set_original_picture(self,img_path:str):
        self.original_picture = encode_image(img_path)
        if self.leaderboardId is not None:
            self.score.ssim_ai_behavior(self.original_picture)

    def add_keyword(self,new_keyword: str,spell_checked: str,source:Literal["AI","User"]):

        # foul language check
        if predict([spell_checked])[0]:
            return "Please do not use foul language."

        keyword=Keyword(
            original=new_keyword,
            spell_checked=spell_checked,
            source=source
        )

        self.keywords.append(keyword)
        return None
    
    def get_keywords(self):
        return [i.spell_checked for i in self.keywords]

    def calculate_vocabulary_score(self):
        used_keywords=[]
        for k in self.keywords:
            if k.spell_checked in self.corrected_sentence:
                used_keywords.append(k)
            else:
                # check whether the tense changed
                with open("data/verb.csv","r") as f:
                    pass

        self.score.set_Vocabulary(used_keywords)

    def set_sentence(self,sentence):
        # language check
        lang=detect(sentence)
        if lang['lang']!="en":
            return "Please enter an English sentence."
        elif lang['score']<0.9:
            return "Please enter a valid English sentence."
        elif predict_prob([sentence])>0.5:
            return "Please avoid offensive language."
        self.sentence=sentence
        self.corrected_sentence=checkSentence(self.sentence)
        self.calculate_vocabulary_score()
        self.score.set_Grammar(self.sentence,self.corrected_sentence)
        self.interpreted_img=gen_image(self.corrected_sentence)

    def get_score(self):
        self.score.set_EffectiveCom()

    def save(self,share=False):
        if share:
            pass
        else:
            pass


    

    


