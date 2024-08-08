from typing import List,Literal,Union
from enum import Enum
import gradio as gr

from ftlangdetect import detect
from profanity_check import predict, predict_prob
import time
import uuid
import base64
import PIL.Image
import io
import requests
import Levenshtein
from function.sentence import genSentences
from function.cefr_few_shot import predict_cefr_en_level
from function.get_embedding import get_embedding,cosine_similarity
import os

import numpy as np

def encode_image(image_path):
    pilImage = PIL.Image.open(io.BytesIO(requests.get(image_path).content))
    return pilImage

class Round():

    def __init__(self,leaderboardId:Union[str,None]=None):
        self.set_id()
        self.cur_step=gr.State(0)
        self.leaderboardId=leaderboardId
        self.original_picture=None
        self.story=None
        self.sentence=None
        self.corrected_sentence=None
        self.is_draft=True
        self.phrases=None
        self.semantic_score=None
        self.vocab_score=None
        self.effectiveness_score=None

    def reset(self):
        self.set_id()
        self.cur_step=gr.State(0)
        self.original_picture=None
        self.story=None
        self.sentence=None
        self.corrected_sentence=None
        self.ai_play=None
        self.is_draft=True
        self.phrases=None
        self.semantic_score=None
        self.vocab_score=None
        self.effectiveness_score=None

    def set_id(self):
        timestamp = str(int(time.time()))
        unique_id = uuid.uuid4().hex
        self.id=f"ID-{timestamp}-{unique_id}"

    def set_original_picture(self,img_path:str):
        if "https:" in img_path:
            image_path = "https:"+img_path.split("https:")[1]
            self.original_picture_path=image_path
            b=io.BytesIO(requests.get(image_path).content)
            base64_image = base64.b64encode(b.read()).decode('utf-8')
            self.original_picture = PIL.Image.open(io.BytesIO(requests.get(image_path).content))
        else:
            self.original_picture_path=img_path
            self.original_picture = PIL.Image.open(img_path)
            with open(os.path.join('data','text_files','01_The tale of two bad mice.txt'),'r') as f:
                self.story=f.read()

    def set_interpreted_picture(self,img):
        if isinstance(img,str):
            self.interpreted_picture = PIL.Image.open(img)
        else:
            self.interpreted_picture = img

    def set_chat_history(self,chat:str):
        self.chat_history=chat

    def set_sentence(self,sentence:str,corrected_sentence:str):
        self.sentence=sentence
        self.corrected_sentence=corrected_sentence

    def semantic_similarity(self):
        if self.semantic_score is not None:
            return self.semantic_score
        self.semantic_score=Levenshtein.ratio(self.sentence,self.corrected_sentence)
        return self.semantic_score

    def cosine_similarity(self):
        
        if self.effectiveness_score is not None:
            return self.effectiveness_score
        
        ai_play = genSentences(self.original_picture_path,self.story)
        self.ai_play=ai_play
        avg_embedding = lambda list: np.mean(list, axis=0)

        user_embedding = get_embedding(self.corrected_sentence)

        result=cosine_similarity(
            user_embedding,
            avg_embedding([get_embedding(i) for i in ai_play])
        )

        self.effectiveness_score=result
        return self.effectiveness_score

    def vocab_difficulty(self):
        if self.vocab_score is not None:
            return self.vocab_score
        few_shot=predict_cefr_en_level(self.corrected_sentence)
        if few_shot == "A1":
            self.vocab_score=0.1
        elif few_shot == "A2":
            self.vocab_score=0.3
        elif few_shot == "B1":
            self.vocab_score=0.5
        elif few_shot == "B2":
            self.vocab_score=0.7
        elif few_shot == "C1":
            self.vocab_score=0.9
        elif few_shot == "C2":
            self.vocab_score=1.0
        return self.vocab_score

    def total_score(self):
        cosine_similarity=self.cosine_similarity()
        semantic_similarity=self.semantic_similarity()
        vocab_difficulty=self.vocab_difficulty()
        total_score=(cosine_similarity+semantic_similarity+vocab_difficulty)/3
        return total_score

    def rank(self):
        total_score=self.total_score()
        if total_score>0.8:
            return "A"
        elif total_score>0.6:
            return "B"
        elif total_score>0.4:
            return "C"
        elif total_score>0.2:
            return "D"
        else:
            return "F"

    def save(self,share=False):
        if share:
            pass
        else:
            pass


