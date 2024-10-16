import spacy
import requests

def get_pos_lemma(word: str, relevant_sentence: str):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(relevant_sentence)
    for token in doc:
        if token.text == word:
            lemma = token.lemma_
            part_of_speech = token.pos_
            return {'pos':part_of_speech, 'lemma':lemma}

def get_meaning(lemma: str, pos: str):
    dict_api="https://api.dictionaryapi.dev/api/v2/entries/en/"
    response = requests.get(dict_api+lemma)
    if response.status_code == 200:
        data = response.json()
        meanings = data[0]['meanings']
        for meaning in meanings:
            if meaning['partOfSpeech'] == pos:
                defintions = meaning['definitions']

                return [defintion['definition'] for defintion in defintions]
    else:
        return "Word not found in the dictionary"
    
def get_sentence_nlp(sentence: str):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(sentence)
    return doc