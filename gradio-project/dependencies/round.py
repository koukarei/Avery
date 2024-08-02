from typing import List,Literal,Union
from enum import Enum

from ftlangdetect import detect
from profanity_check import predict, predict_prob
from sklearn.metrics.pairwise import cosine_similarity
import time
import uuid
import base64
import PIL.Image
import io
import requests
import Levenshtein
from function.sentence import genSentences
import os

import torch
import clip

def encode_image(image_path):
    pilImage = PIL.Image.open(io.BytesIO(requests.get(image_path).content))
    return pilImage

class Round():

    def __init__(self,leaderboardId:Union[str,None]=None):
        self.set_id()
        self.leaderboardId=leaderboardId
        self.original_picture=None
        self.sentence=None
        self.corrected_sentence=None
        self.is_draft=True
        self.phrases=None

    def set_id(self):
        timestamp = str(int(time.time()))
        unique_id = uuid.uuid4().hex
        self.id=f"ID-{timestamp}-{unique_id}"

    def set_original_picture(self,img_path:str,testing=False):
        if testing:
            self.original_picture_path=img_path
            self.original_picture = PIL.Image.open(img_path)
        else:
            image_path = "https:"+img_path.split("https:")[1]
            self.original_picture_path=image_path
            b=io.BytesIO(requests.get(image_path).content)
            base64_image = base64.b64encode(b.read()).decode('utf-8')
            self.original_picture = PIL.Image.open(io.BytesIO(requests.get(image_path).content))

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
        return Levenshtein.ratio(self.sentence,self.corrected_sentence)

    def cosine_similarity(self):
        # デバイスの指定
        device = "cuda" if torch.cuda.is_available() else "cpu"

        # CLIPモデルの読み込み
        model, preprocess = clip.load("ViT-B/32", device=device)

        # 画像の読み込みと前処理
        image = preprocess(self.original_picture).unsqueeze(0).to(device)

        # テキストの読み込みと前処理
        target_text = clip.tokenize([self.corrected_sentence]).to(device)
        ai_play = genSentences(self.original_picture_path)
        phrase_text = clip.tokenize(ai_play).to(device)
        self.ai_play=ai_play
        

        # 画像とテキストの類似度を計算
        with torch.no_grad():
            image_features = model.encode_image(image)
            text_features = model.encode_text(phrase_text)
            
            similarity = (image_features @ text_features.T)

            target_text_features = model.encode_text(target_text)
            
            target_similarity = (image_features @ target_text_features.T)
            normalized_similarity = target_similarity / similarity.norm(dim=-1, keepdim=True)
            result=normalized_similarity.tolist()[0][0]

        return result

    def vocab_difficulty(self):
        return 0

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


