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

    def set_id(self):
        timestamp = str(int(time.time()))
        unique_id = uuid.uuid4().hex
        self.id=f"ID-{timestamp}-{unique_id}"
        return self.id

    def set_original_picture(self,img_path:str):
        if "https:" in img_path:
            image_path = "https:"+img_path.split("https:")[1]
            original_picture_path=image_path
            b=io.BytesIO(requests.get(image_path).content)
            base64_image = base64.b64encode(b.read()).decode('utf-8')
            original_picture = PIL.Image.open(io.BytesIO(requests.get(image_path).content))
        else:
            original_picture_path=img_path
            original_picture = PIL.Image.open(img_path)
            with open(os.path.join('data','text_files','01_The tale of two bad mice.txt'),'r') as f:
                story=f.read()
        return original_picture_path,original_picture,story

    def set_interpreted_picture(self,img):
        if isinstance(img,str):
            interpreted_picture = PIL.Image.open(img)
        else:
            interpreted_picture = img
        return interpreted_picture

    def semantic_similarity(self,sentence:str,corrected_sentence:str):
        semantic_score=Levenshtein.ratio(sentence,corrected_sentence)
        return semantic_score

    def cosine_similarity(self,original_picture_path:str,story:str,corrected_sentence:str):
        
        ai_play = genSentences(original_picture_path,story)
        
        avg_embedding = lambda list: np.mean(list, axis=0)

        user_embedding = get_embedding(corrected_sentence)

        result=cosine_similarity(
            user_embedding,
            avg_embedding([get_embedding(i) for i in ai_play])
        )

        return result,ai_play

    def vocab_difficulty(self,corrected_sentence:str):
        few_shot=predict_cefr_en_level(corrected_sentence)
        if few_shot == "A1":
            vocab_score=0.1
        elif few_shot == "A2":
            vocab_score=0.3
        elif few_shot == "B1":
            vocab_score=0.5
        elif few_shot == "B2":
            vocab_score=0.7
        elif few_shot == "C1":
            vocab_score=0.9
        elif few_shot == "C2":
            vocab_score=1.0
        return vocab_score

    def total_score(self,sentence:str,corrected_sentence:str,original_picture_path:str,story:str):
        cosine_similarity,ai_example=self.cosine_similarity(original_picture_path,story,corrected_sentence)
        semantic_similarity=self.semantic_similarity(sentence,corrected_sentence)
        vocab_difficulty=self.vocab_difficulty(corrected_sentence)
        total_score=(cosine_similarity+semantic_similarity+vocab_difficulty)/3
        rank=self.rank(total_score)
        return cosine_similarity,semantic_similarity,vocab_difficulty,total_score,rank,ai_example

    def rank(self,total_score):
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


