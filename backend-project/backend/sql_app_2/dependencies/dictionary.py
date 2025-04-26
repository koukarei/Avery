import requests
import time, asyncio
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
        