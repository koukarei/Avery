from typing import List,Literal,Union
from enum import Enum

import PIL.Image
import io
import requests
import Levenshtein
from .sentence import genSentences
from .cefr_few_shot import predict_cefr_en_level
from .get_embedding import get_embedding,cosine_similarity

import numpy as np

def encode_image(image_path):
    pilImage = PIL.Image.open(io.BytesIO(requests.get(image_path).content))
    return pilImage

def semantic_similarity(sentence:str,corrected_sentence:str):
    semantic_score=Levenshtein.ratio(sentence,corrected_sentence)
    return semantic_score

def cosine_similarity_to_ai(ai_play: List[str],corrected_sentence:str):
    
    avg_embedding = lambda list: np.mean(list, axis=0)

    user_embedding = get_embedding(text=corrected_sentence)

    result=cosine_similarity(
        user_embedding,
        avg_embedding([get_embedding(text=i) for i in ai_play])
    )

    return result

def vocab_difficulty(corrected_sentence:str):
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

def rank(total_score):
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



