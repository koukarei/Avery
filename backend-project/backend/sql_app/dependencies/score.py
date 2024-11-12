from typing import List,Literal,Union
from enum import Enum

import PIL.Image
import io
import requests
import Levenshtein

import torch

from lavis.models import load_model_and_preprocess
from lavis.processors import load_processor

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model, vis_processors, text_processors = load_model_and_preprocess("blip2_image_text_matching", "pretrain", device=device, is_eval=True)

import stanza
import language_tool_python
import time

import numpy as np

stanza.download('en')
en_nlp = stanza.Pipeline('en', processors='tokenize,pos,constituency', package='default_accurate')

from transformers import OpenAIGPTTokenizer, OpenAIGPTLMHeadModel
from transformers import GPT2Tokenizer, GPT2LMHeadModel

def model_init(model_string, cuda):
    if model_string.startswith("gpt2"):
        tokenizer = GPT2Tokenizer.from_pretrained(model_string)
        model = GPT2LMHeadModel.from_pretrained(model_string)
    else:
        tokenizer = OpenAIGPTTokenizer.from_pretrained(model_string)
        model = OpenAIGPTLMHeadModel.from_pretrained(model_string)
    model.eval()
    if cuda:
        model.to('cuda')
    print("Model init")
    return model, tokenizer

model, tokenizer = model_init('gpt2', False)

def get_loss_pretrained(text, cuda=False):
    assert model is not None
    assert tokenizer is not None
    input_ids = torch.tensor(tokenizer.encode(text)).unsqueeze(0)  # Batch size 1
    if cuda:
        input_ids = input_ids.to('cuda')
    with torch.no_grad():
        outputs = model(input_ids, labels=input_ids)
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
            time.sleep(1)
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

def perplexity(sentence, cut_points):
  log_probs=[]
  for i,p in enumerate(cut_points):
    if i+1 == len(cut_points):
      t=sentence
    else:
      t=sentence[:p]
    log_probs.append(get_loss_pretrained(t))
    perplexity_value = np.exp(-np.mean(log_probs))
  return {
     'perplexity':perplexity_value
  }

def calculate_content_score(image_path: str, sentence: str):
    raw_image = PIL.Image.open(image_path).convert("RGB")
    img = vis_processors["eval"](raw_image).unsqueeze(0).to(device)
    txt = text_processors["eval"](sentence)

    itm_output = model({"image": img, "text_input": txt}, match_head="itm")
    itm_scores = torch.nn.functional.softmax(itm_output, dim=1)
    content_score = itm_scores[:, 1].item()*100
    # print(f'The image and text are matched with a probability of {itm_scores[:, 1].item():.3%}')

    # itc_score = model({"image": img, "text_input": txt}, match_head='itc')
    # print('The image feature and text feature has a cosine similarity of %.4f'%itc_score)
    return {
       'content_score':content_score
    }

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
      perplexity: int,
      f_word: int,
      f_bigram: int,
      content_score: int
):
    output={
       'grammar_score':5-len(n_grammar_errors) if len(n_grammar_errors)<5 else 0,
       'spelling_score':(n_words-len(n_spelling_errors))/n_words
    }

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
    output['vividness_score'] = f_word
    
    perplexity_score = perplexity*100
    convention = f_bigram-perplexity_score
    output['convention']= convention
    
    output['structure_score']= n_clauses if n_clauses < 3 else 3

    lang_quality = sum(output.values())
    output['total_score'] = lang_quality*content_score

    output['lang_quality']=lang_quality
    output['content_score']=content_score

    return output

def calculate_score_init(image_path: str, sentence: str):
   doc = en_nlp(sentence)
   words=[w for s in doc.sentences for w in s.words]
   factors=n_wordsNclauses(
      doc=doc,
      words=words
   )

   factors.update(grammar_spelling_errors(sentence))

   cut_points=[w.end_char+1 for w in words if w.start_char != 0]
   factors.update(perplexity(
      sentence=sentence,
      cut_points=cut_points
   ))

   factors.update(frequency_score(words=words))

   factors.update(calculate_content_score(image_path=image_path,sentence=sentence))
   
   output=calculate_score(**factors)

   return output

# def semantic_similarity(sentence:str,corrected_sentence:str):
#     semantic_score=Levenshtein.ratio(sentence,corrected_sentence)
#     return semantic_score

# def cosine_similarity_to_ai(ai_play: List[str],corrected_sentence:str):
    
#     avg_embedding = lambda list: np.mean(list, axis=0)

#     user_embedding = get_embedding(text=corrected_sentence)

#     result=cosine_similarity(
#         user_embedding,
#         avg_embedding([get_embedding(text=i) for i in ai_play])
#     )

#     return float(result[0]) if isinstance(result, np.ndarray) else float(result)

# def vocab_difficulty(corrected_sentence:str):
#     few_shot=predict_cefr_en_level(corrected_sentence)
#     if few_shot == "A1":
#         vocab_score=0.1
#     elif few_shot == "A2":
#         vocab_score=0.3
#     elif few_shot == "B1":
#         vocab_score=0.5
#     elif few_shot == "B2":
#         vocab_score=0.7
#     elif few_shot == "C1":
#         vocab_score=0.9
#     elif few_shot == "C2":
#         vocab_score=1.0
#     return vocab_score

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



