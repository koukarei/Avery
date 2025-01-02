import stanza
import requests
import time

stanza.download('en')
en_nlp = stanza.Pipeline('en', processors='tokenize,mwt,pos,lemma', package='default_accurate')

def get_pos_lemma(word: str, relevant_sentence: str):
    doc = en_nlp(relevant_sentence)
    for sentence in doc.sentences:
        for token in sentence.words:
            if token.text == word:
                lemma = token.lemma
                part_of_speech = token.pos
                return {'pos':part_of_speech, 'lemma':lemma}

def get_meaning(lemma: str, pos: str):
    dict_api="https://api.dictionaryapi.dev/api/v2/entries/en/"
    response = requests.get(dict_api+lemma, timeout=5)
    while response.status_code == 429:
        time.sleep(3)
        response = requests.get(dict_api+lemma, timeout=5)
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
    doc = en_nlp(sentence)
    words = [word for sentence in doc.sentences for word in sentence.words if word.pos != 'PUNCT']
    return words

def get_pos_bulk(words: list[str], relevant_sentence: str):
    doc = en_nlp(relevant_sentence)
    words_pos_lemma = {}
    for sentence in doc.sentences:
        for token in sentence.words:
            if token.lemma in words:
                words_pos_lemma[token.lemma] = {
                    'pos': token.pos,
                    'lemma': token.lemma
                }
    return words_pos_lemma