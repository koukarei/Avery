import spacy
import requests

def get_meaning(word: str, relevant_sentence: str):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(relevant_sentence)
    for token in doc:
        if token.text == word:
            lemma = token.lemma_
            part_of_speech = token.pos_
            break
    dict_api="https://api.dictionaryapi.dev/api/v2/entries/en/"
    response = requests.get(dict_api+lemma)
    if response.status_code == 200:
        data = response.json()
        meanings = data[0]['meanings']
        for meaning in meanings:
            if meaning['partOfSpeech'] == part_of_speech:
                defintions = meaning['definitions']
                return [defintion['definition'] for defintion in defintions]
    else:
        return "Word not found in the dictionary"