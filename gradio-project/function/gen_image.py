from openai import OpenAI
import urllib.request 
from dependencies.round import Round
import spacy
import pytextrank
import random

def save_image(url, filename):
    urllib.request.urlretrieve(url, filename)

def gen_image(sentence,size="1024x1024",quality="standard",n=1):
    client = OpenAI()

    while True:
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=sentence,
                size=size,
                quality=quality,
                n=n,
                )
            break
        except Exception as e:
            print(f"Error: {e}")
            continue
    return response.data[0].url

def generate_interpretion(sentence):
    rules="""
            Generate a realistic image for the sentence above.
            The image must not contain any text, wording or sentence.
            The image must not be a collage. The image must be a single image.
            """

    prompt = "{} \n {}".format(
        sentence,
        rules
    )
    url = gen_image(prompt)
    return url

class GenerateOriginalImage:
    def __init__(self,story_text) -> None:
        self.nlp = spacy.load("en_core_web_sm")
        self.nlp.add_pipe("textrank")
        self.doc = self.nlp(story_text)
    
    def select_phrases(self):
        phrases = random.choices(self.doc._.phrases, k=20)
        return phrases
    
    def get_original_images(self,round:Round):
        urls=[]
        for i in range(3):
            phrases = self.select_phrases()
            str_phrases = "\n".join([f"{phrase.text}: {phrase.rank}" for phrase in phrases])
            prompt = """
            Select 5 to 10 phrases in the phrase list below.
            Your selection can refer to the rank of the phrases and the visionary of the phrases.
            Generate a realistic image based on the selected phrases.
            The image should include one or more characters.
            The scene can be a landscape, a cityscape, or a room.
            For example, the image can be a person standing in a room, a cat playing in a garden, or a car driving on a road.
            The image must not contain any text, wording or sentence.
            The image must not be a collage. The image must be a single image.
            Phrase: Rank
            {}
            """.format(str_phrases)
            round.phrases = phrases
            url = gen_image(prompt)
            urls.append(url)
        return urls

