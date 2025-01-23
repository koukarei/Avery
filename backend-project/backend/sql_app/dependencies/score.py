from typing import List,Literal,Union
from fastapi import HTTPException
from enum import Enum

import PIL.Image, cv2
import io, os, asyncio
import requests
from . import util

import torch
from skimage.metrics import structural_similarity as ssim

import language_tool_python
import time

import numpy as np

def get_loss_pretrained(perplexity_model, tokenizer,text, descriptions: list, cuda=False):
    
    question = "Conclude the following sentence: "
    d = '\n* '.join(descriptions)
    question_d = f"Question: {question} {d}"

    # if description is too long, cut it in half
    if len(question_d) > 512:
      descriptions = descriptions[:len(descriptions)//2]
      d = '\n* '.join(descriptions)
      question_d = f"Question: {question} {d}"

    # if description is still too long, cut it to the first element
    if len(question_d) > 512:
       descriptions = descriptions[0]
       question_d = f"Question: {question} {descriptions}"

    # if description is still too long, just use a generic question
    if len(question_d) > 512:
       question_d = f"Question: Describe an image from a story"
    
    text_to_encode = f"{question_d}\n Answer:{text}"
    input_ids = torch.tensor(tokenizer.encode(text_to_encode)).unsqueeze(0)  # Batch size 1
    if cuda:
        input_ids = input_ids.to('cuda')
    with torch.no_grad():
        outputs = perplexity_model(input_ids, labels=input_ids)
    loss, logits = outputs[:2]
    sentence_prob = loss.item()
    return sentence_prob

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

def grammar_spelling_errors(sentence: str, en_nlp):
    doc = en_nlp(sentence)
    tool = language_tool_python.LanguageTool('en-US')
    spellings=[]
    grammars=[]
    for s in doc.sentences:
      matches = tool.check(s.text)
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

def perplexity(perplexity_model, tokenizer,sentence, cut_points, descriptions):
  log_probs=[]
  for i,p in enumerate(cut_points):
    if i+1 == len(cut_points):
      t=sentence
    else:
      t=sentence[:p]
    log_probs.append(get_loss_pretrained(perplexity_model, tokenizer,t, descriptions))
    perplexity_value = np.exp(-np.mean(log_probs))
  return {
     'perplexity':perplexity_value
  }

async def calculate_content_score(
      image: str, 
      sentence: str
      ):
    
    BLIP2_URL = os.getenv("BLIP2_URL")
    # BLIP2_URL = "http://blip2:7874/fake_content_score"

    status_code = 503
    counter = 0
    while status_code == 503:
      if counter >0:
        await asyncio.sleep(2)
      response = requests.post(
          url=BLIP2_URL, data={"sentence":sentence, "image": image}, timeout=30
      )
      status_code = response.status_code
      counter += 1
    response.raise_for_status()
    return response.json()

def calculate_content_score_celery(
      image: str,
      sentence: str
):
    
    BLIP2_URL = os.getenv("BLIP2_URL")
    # BLIP2_URL = "http://blip2:7874/fake_content_score"

    try:
      status_code = 503
      counter = 0
      while status_code == 503:
        if counter >0:
          time.sleep(2)
        response = requests.post(
            url=BLIP2_URL, data={"sentence":sentence, "image": image}, timeout=120
        )
        status_code = response.status_code
        counter += 1
      response.raise_for_status()
      return response.json()
    except requests.exceptions.RequestException as e:
      raise HTTPException(status_code=500, detail="BLIP2 server error: {e}")

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
      content_score: int,
      **kwargs
):
    output={
       'grammar_score':5-n_grammar_errors if n_grammar_errors<5 else 0,
       'spelling_score':((n_words-n_spelling_errors)/n_words)*5
    }

    vividness = n_adj + n_adv + n_pronouns + n_prepositions + n_conjunctions
    output['vividness_score']=vividness if vividness < 5 else 5

    convention = perplexity > 0.01
    output['convention']= int(convention)
    
    output['structure_score']= n_clauses if n_clauses < 3 else 3

    lang_quality = sum(output.values())
    full_score = 19*80
    total_score = int(round(lang_quality*content_score)/full_score * 100)
    output['total_score'] = total_score

    output['lang_quality']=lang_quality
    output['content_score']=content_score

    return output

async def calculate_score_init(
      en_nlp,
      perplexity_model,
      tokenizer,
      image: str, 
      sentence: str,
      descriptions: list
):
   doc = en_nlp(sentence)
   words=[w for s in doc.sentences for w in s.words]
   factors=n_wordsNclauses(
      doc=doc,
      words=words
   )

   factors.update(grammar_spelling_errors(sentence, en_nlp))

   cut_points=[w.end_char+1 for w in words if w.start_char != 0]
   factors.update(perplexity(
        perplexity_model=perplexity_model,
        tokenizer=tokenizer,
      sentence=sentence,
      cut_points=cut_points,
      descriptions=descriptions
   ))

   # await factors.update(frequency_score(words=words))

   factors.update(await calculate_content_score(
      image=image,
      sentence=sentence
   ))
   
   output=calculate_score(**factors)

   return factors, output

def image_similarity(image1, image2):
    # Read images using OpenCV
    img1 = util.base64_to_cv(image1)
    img2 = util.base64_to_cv(image2)

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
    max_score = 100
    if total_score>(max_score*0.9):
        return "A"
    elif total_score>(max_score*0.8):
        return "B"
    elif total_score>(max_score*0.7):
        return "C"
    elif total_score>(max_score*0.5):
        return "D"
    elif total_score>(max_score*0.4):
        return "E"
    else:
        return "F"



