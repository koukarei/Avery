from typing import List,Literal,Union
from fastapi import HTTPException
from enum import Enum

import PIL.Image
import io
import requests

import torch

import os

import cv2
from skimage.metrics import structural_similarity as ssim

import stanza
import language_tool_python
import time

import numpy as np

def get_loss_pretrained(perplexity_model, tokenizer,text, cuda=False):
    input_ids = torch.tensor(tokenizer.encode(text)).unsqueeze(0)  # Batch size 1
    if cuda:
        input_ids = input_ids.to('cuda')
    with torch.no_grad():
        outputs = perplexity_model(input_ids, labels=input_ids)
    loss, logits = outputs[:2]
    sentence_prob = loss.item()
    return sentence_prob

def encode_image(image_path):
    pilImage = PIL.Image.open(io.BytesIO(requests.get(image_path).content))
    return pilImage

def analysis_word(words):
  output = {
      "n_words":0,
      "n_conjunctions":0,
      "n_adj":0,
      "n_adv":0,
      "n_pronouns":0,
      "n_prepositions":0,
  }
  
  for word in words:
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

def n_wordsNclauses(doc, words):
    output=analysis_word(words)
    clauses = []
    for sentence in doc.sentences:
        tree = sentence.constituency
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

    return {
       'grammar_error':grammars,
       'spelling_error':spellings,
       'n_grammar_errors':len(grammars),
       'n_spelling_errors':len(spellings),
    }

def frequency_word_ngram(words,n_gram=2):
  google_ngram="https://books.google.com/ngrams/json?year_start=2000&content="
  
  words = [w.text for w in words if w.pos != 'PUNCT']
  
  ngrams = set(words.copy())
  for i in range(2,n_gram+1):
    for j in range(0,len(words)):
      ngrams.add('%20'.join(words[j:j+i]))
  output=[]
  for i, ngram in enumerate(ngrams):
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
          if i != len(ngrams)-1:
            time.sleep(3)
      else:
        print(f"Error: {response.status_code}")
  if not output:
    raise ValueError("No data found")
  return output

def frequency_score(words):
   freq=frequency_word_ngram(words)
   f_word=np.mean([i['freq'] for i in freq if i['type']=='word'])
   f_bigram=np.mean([i['freq'] for i in freq if i['type']=='ngram'])
   return {
         "f_word":f_word,
         "f_bigram":f_bigram
   }

def perplexity(perplexity_model, tokenizer,sentence, cut_points):
  log_probs=[]
  for i,p in enumerate(cut_points):
    if i+1 == len(cut_points):
      t=sentence
    else:
      t=sentence[:p]
    log_probs.append(get_loss_pretrained(perplexity_model, tokenizer,t))
    perplexity_value = np.exp(-np.mean(log_probs))
  return {
     'perplexity':perplexity_value
  }

def calculate_content_score(
      image_path: str, 
      sentence: str
      ):
    
    BLIP2_URL = os.getenv("BLIP2_URL")
    # BLIP2_URL = "http://blip2:7874/fake_content_score"
    if isinstance(image_path, str):
      image_filename = image_path.split("/")[-1]
    elif isinstance(image_path, os.PathLike):
      image_filename = image_path.name
    else:
       raise ValueError("image_path must be a string or a PathLike object")

    try:
      with open(image_path, "rb") as f:
        status_code = 503
        counter = 0
        while status_code == 503:
          if counter >0:
            time.sleep(2)
          response = requests.post(
              url=BLIP2_URL, data={"sentence":sentence}, files={"image": (image_filename, f, "image/jpeg")}, timeout=30
          )
          status_code = response.status_code
          counter += 1
      response.raise_for_status()
      return response.json()
    except requests.exceptions.RequestException as e:
      raise HTTPException(status_code=500, detail="BLIP2 server error")

def calculate_score(
      n_grammar_errors: int,
      n_spelling_errors: int,
      n_words: int,
      n_conjunctions: int,
      n_adj: int,
      n_adv: int,
      n_pronouns: int,
      n_prepositions: int,
      n_clauses: int,
      perplexity: float,
      f_word: float,
      f_bigram: float,
      content_score: int,
      **kwargs
):
    output={
       'grammar_score':5-n_grammar_errors if n_grammar_errors<5 else 0,
       'spelling_score':((n_words-n_spelling_errors)/n_words)*5
    }

    output['vividness_score']=0
    output['vividness_score']+= 1 if n_adj else 0
    output['vividness_score']+= 1 if n_adv else 0
    output['vividness_score']+= 1 if n_pronouns else 0
    output['vividness_score']+= 1 if n_prepositions else 0
    output['vividness_score']+= 1 if n_conjunctions else 0
    
    descriptive_words = (n_adj + n_adv + n_pronouns + n_prepositions + n_conjunctions)/n_words
    if descriptive_words > 0.5:
        output['vividness_score']+= 2
    else:
       output['vividness_score']+= descriptive_words*4
    output['vividness_score'] += f_word
    output['vividness_score'] = output['vividness_score'] if output['vividness_score'] < 8 else 8
    output['vividness_score'] = output['vividness_score'] / 8 * 5

    perplexity_score = perplexity
    f_bigram = f_bigram if f_bigram < 5 else 5
    convention = f_bigram-perplexity_score
    output['convention']= convention
    
    output['structure_score']= n_clauses if n_clauses < 3 else 3

    lang_quality = sum(output.values())
    output['total_score'] = int(round(lang_quality*content_score))

    output['lang_quality']=lang_quality
    output['content_score']=content_score

    return output

def calculate_score_init(
      en_nlp,
      perplexity_model,
      tokenizer,
      image_path: str, 
      sentence: str
):
   doc = en_nlp(sentence)
   words=[w for s in doc.sentences for w in s.words]
   factors=n_wordsNclauses(
      doc=doc,
      words=words
   )

   factors.update(grammar_spelling_errors(sentence))

   cut_points=[w.end_char+1 for w in words if w.start_char != 0]
   factors.update(perplexity(
        perplexity_model=perplexity_model,
        tokenizer=tokenizer,
      sentence=sentence,
      cut_points=cut_points
   ))

   factors.update(frequency_score(words=words))

   factors.update(calculate_content_score(
      image_path=image_path,
      sentence=sentence
   ))
   
   output=calculate_score(**factors)

   return factors, output

def image_similarity(image1_path, image2_path):
    # Read images using OpenCV
    img1 = cv2.imread(image1_path)
    img2 = cv2.imread(image2_path)

    # Check if images were read successfully
    if img1 is None or img2 is None:
        raise ValueError("Could not read one or both images")

    # Get image dimensions
    height = min(img1.shape[0], img2.shape[0])
    width = min(img1.shape[1], img2.shape[1])

    # Resize images
    img1 = cv2.resize(img1, (width, height))
    img2 = cv2.resize(img2, (width, height))

    # Convert to grayscale
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # Calculate histograms
    hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
    hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])

    # Normalize histograms
    cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
    cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)

    # Compare histograms
    similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

    # Calculate SSIM
    ssim_score = ssim(gray1, gray2)

    return {
        "hist_similarity": similarity,
        "ssim_score": ssim_score
    }

def rank(total_score):
    if total_score>2100:
        return "A"
    elif total_score>1800:
        return "B"
    elif total_score>1600:
        return "C"
    elif total_score>1000:
        return "D"
    elif total_score>500:
        return "E"
    else:
        return "F"



