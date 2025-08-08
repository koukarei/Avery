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
    if text is None or text.strip() == "":
        return ""
    if detect_lang(text) == target_lang:
        return text
    client=OpenAI()
    if target_lang not in ['en', 'ja']:
        raise ValueError("Target language must be either 'en' or 'ja'")
    
    if target_lang == 'en':
        response = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[
                {"role": "system", "content": f"Translate the following text to English."},
                {"role": "user", "content": text}
            ]
        )
    elif target_lang == 'ja':
        response = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[
                {"role": "system", "content": f"以下の内容を日本語に翻訳してください。"},
                {"role": "user", "content": text}
            ]
        )
    return response.choices[0].message.content.strip()

def cal_frequency(text: str, lang: str = 'en') -> dict:
    if lang not in ['en', 'ja']:
        raise ValueError("Language must be either 'en' or 'ja'")
    if lang == 'ja':
        nlp = spacy.load("ja_core_news_sm")
    else:
        nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    frequency = {}
    
    for token in doc:
        if not token.is_stop and not token.is_punct:
            frequency[token.text] = frequency.get(token.text, 0) + 1
            
    return frequency