import spacy
import re
from openai import OpenAI

def detect_lang(text: str) -> str:
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
        return 'jp'
    elif re.search(r'[a-zA-Z]', text):
        return 'en'
    else:
        return 'Unknown'
    
def translate_text(text: str, target_lang: str = 'en') -> str:
    if detect_lang(text) == target_lang:
        return text
    client=OpenAI()
    response = client.chat.completions.create(
        model="gpt-4.1-nano-2025-04-14",
        messages=[
            {"role": "system", "content": f"Translate the following text to {target_lang}."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content.strip()

def cal_frequency(text: str) -> dict:
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    frequency = {}
    
    for token in doc:
        if not token.is_stop and not token.is_punct:
            frequency[token.text] = frequency.get(token.text, 0) + 1
            
    return frequency