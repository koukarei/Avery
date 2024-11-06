from typing import List,Literal,Union
from enum import Enum

import PIL.Image
import io
import requests
import Levenshtein
from .cefr_few_shot import predict_cefr_en_level
from .get_embedding import get_embedding,cosine_similarity
import stanza
import language_tool_python

import numpy as np

stanza.download('en')
en_nlp = stanza.Pipeline('en', processors='tokenize,pos,constituency', package='default_accurate')

def encode_image(image_path):
    pilImage = PIL.Image.open(io.BytesIO(requests.get(image_path).content))
    return pilImage

def analysis_word(doc):
  output = {
      "n_words":0,
      "n_conjunctions":0,
      "n_adj":0,
      "n_adv":0,
      "n_pronouns":0,
      "n_prepositions":0,
  }
  for i, sent in enumerate(doc.sentences):
      print("[Sentence {}]".format(i+1))
      for word in sent.words:
          # print("{:12s}\t{:12s}\t{:6s}\t{:d}\t{:12s}".format(\
          #       word.text, word.lemma, word.pos, word.head, word.deprel))
          output["n_words"]+=1
          if word.pos=="SCONJ":
            output["n_conjunctions"]+=1
          elif word.pos=="ADJ":
            output["n_adj"]+=1
          elif word.pos=="ADV":
            output["n_adv"]+=1
          elif word.pos=="PRON":
            output["n_pronouns"]+=1
          elif word.pos=="ADP":
            output["n_prepositions"]+=1
  return output

def n_wordsNclauses(sentence: str):
    doc = en_nlp(sentence)
    output=analysis_word(doc)

    for sentence in doc.sentences:
        tree = sentence.constituency
        clauses = []
        words_to_visit = [tree]
        
        while words_to_visit:
            cur_word = words_to_visit.pop()
            if cur_word.label == 'S':
                clauses.append(cur_word)
            words_to_visit.extend(cur_word.children)
        
        n_clause = len(clauses)
        output["n_clauses"]=n_clause
    return output

def grammar_spelling_errors(sentence: str):
    tool = language_tool_python.LanguageTool('en-US')
    matches = tool.check(sentence)
    spellings=[]
    grammars=[]
    for m in matches:
       if m.ruleId == 'MORFOLOGIK_RULE_EN_US':
          spellings.append(m)
       else:
          grammars.append(m)

    n_words=len(sentence.split())
    return {
       'grammar_error':grammars,
       'spelling_error':spellings,
       'grammar_score':len(grammars) if len(grammars)<5 else 5,
       'spelling_score':(n_words-len(spellings))/n_words
    }

def frequency_word_ngram(text,n_gram=2):
  doc=en_nlp(text)
  google_ngram="https://books.google.com/ngrams/json?year_start=2000&content="
  words = []
  
  for sentence in doc.sentences:
    words.extend([w.text for w in sentence.words if w.pos != 'PUNCT'])
  
  ngrams = set(words.copy())
  for i in range(2,n_gram+1):
    for j in range(0,len(words)):
      ngrams.add('%20'.join(words[j:j+i]))
  output=[]
  for ngram in ngrams:
      response = requests.get(google_ngram + ngram)
      if response.status_code == 200:
          data = response.json()
          if data:
            freq = np.mean(data[0]['timeseries'])
          else:
            freq = 0
          output.append({'text':ngram,
                         'type':'ngram' if '%20' in ngram else 'word',
                         'freq':freq})
  return output

def frequency_score(text):
   freq=frequency_word_ngram(text)
   f_word=np.mean([i['freq'] for i in freq if i['type']=='word'])
   f_bigram=np.mean([i['freq'] for i in freq if i['type']=='ngram'])
   return {
         "f_word":f_word,
         "f_bigram":f_bigram
   }

def perplexity(sentence: str):
    np.exp()

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

    return float(result[0]) if isinstance(result, np.ndarray) else float(result)

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



