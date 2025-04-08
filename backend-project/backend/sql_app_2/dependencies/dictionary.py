import stanza
from stanza.pipeline.core import DownloadMethod
import requests
import time, asyncio

#stanza.download('en')
class Dictionary:
    def __init__(self):
        self.en_nlp = stanza.Pipeline('en', processors='tokenize,mwt,pos,lemma,constituency', package='default_accurate', download_method=DownloadMethod.REUSE_RESOURCES)

    def get_pos_lemma(self, word: str, relevant_sentence: str):
        doc = self.en_nlp(relevant_sentence)
        for sentence in doc.sentences:
            for token in sentence.words:
                if token.text == word:
                    lemma = token.lemma
                    part_of_speech = token.pos
                    return {'pos':part_of_speech, 'lemma':lemma}

    async def get_meaning(self, lemma: str, pos: str):
        dict_api="https://api.dictionaryapi.dev/api/v2/entries/en/"
        response = requests.get(dict_api+lemma, timeout=5)
        while response.status_code == 429:
            await asyncio.sleep(3)
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
        
    def get_sentence_nlp(self, sentence: str):
        doc = self.en_nlp(sentence)
        words = [word for sentence in doc.sentences for word in sentence.words if word.pos != 'PUNCT']
        return words

    def get_pos_bulk(self, words: list[str], relevant_sentence: str):
        doc = self.en_nlp(relevant_sentence)
        words_pos_lemma = {}
        for sentence in doc.sentences:
            for token in sentence.words:
                if token.lemma in words:
                    words_pos_lemma[token.lemma] = {
                        'pos': token.pos,
                        'lemma': token.lemma
                    }
        return words_pos_lemma