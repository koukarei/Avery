import google.generativeai as genai
import google.ai.generativelanguage_v1beta.types.content as genlang_content
# https://ai.google.dev/api/python/google/generativeai/GenerativeModel?_gl=1*7pk6lc*_up*MQ..*_ga*NzQwNTA2OTc0LjE3MjA1MDg0Mzc.*_ga_P1DBVKWT6V*MTcyMDUwODQzNi4xLjAuMTcyMDUwODQzNi4wLjAuMTI4MjQwOTIyMQ..
# 必要モジュールのインポート
import io
import requests
import base64
import PIL.Image
from PIL.PngImagePlugin import PngImageFile
from PIL.JpegImagePlugin import JpegImageFile
import os
import datetime

# os.environを用いて環境変数を表示させます
GENAI_API_KEY=os.environ['GEMINI_API_KEY']

def convert_image(img):
    if img:
        if isinstance(img, PngImageFile):
            return img
        elif isinstance(img, JpegImageFile):
            return img
        try:
            pilImage = PIL.Image.open(io.BytesIO(requests.get(img).content))
        except:
            pilImage = PIL.Image.open(img)
        return pilImage
    return None

def convert_history(original):
    # raw history format=list[messages], where messages=[{"sender": "user", "content": "Hello"}, {"sender": "model", "content": "How are you?"}]
    # new converted history format=[
    #     {"parts": [{"text": "Hello"}]},
    #     {"parts": [{"text": "How are you?"}]}
    # ]

    target = {
        "contents": [],
    }
    
    # Extract data from the original format
    for entry in original:
        target["contents"].append({
            "role": entry["sender"],
            "parts": [{"text": entry["content"]}]
        })
    
    return target['contents']
        

class Hint_Chatbot:
    def __init__(self):
        genai.configure(api_key=GENAI_API_KEY)
        
        system_prompt = f"""
Your name is Avery. 
You are a robot. 
You are playing a game with a human and a robot, Skyler.
You are cooperating with a human to describe an image.
Skyler will generate an image of your sentences.
Higher score means better description of the image.
You and the human aim to get the highest score.
Use simple English to communicate with the user.
When you receive an image and a story, you should repy: The image is imported to my system. You can ask me for a hint.
The user will ask you hint to describe the image. 
You should assist them with a minimum but accurate hint to them.
You must talk like a robot, like the Baymax of Disney.
You do not know other languages except English.
If the user does not use English, you should ask them to use English.
If the user give you a sentence to describe the image, you can give feedback to user to correct the sentence.
If the user's sentence fits to original image, you should ask the user to import the sentence to the system.
        """

        model=genai.GenerativeModel(
            model_name="models/gemini-1.5-flash",
            system_instruction=system_prompt,
            # generation_config=generation_config
        )

        self.model=model
    
    def nextResponse(self, ask_for_hint: str, chat_history: list, original_image):
        messages=[]
        messages.append(convert_image(original_image))
        messages.append(ask_for_hint)

        if len(messages)==0:
            print("No messages")
            return {}

        try:
            chat=self.model.start_chat(history=convert_history(chat_history))
            response=chat.send_message(messages)
            return response.text
        except Exception as e:
            print(f"Error: {e}")
            print(f"Messages: {messages}")
            return {}
        

    def get_result(self,generated_image, sentence,scoring,original_image,chat_history):
        system_prompt = f"""
Your name is Avery. 
You are a robot. 
You are playing a game with a human and a robot, Skyler.
You are cooperating with a human to describe an image.
Skyler will generate an image of your sentences.
Higher score means better description of the image.
You and the human aim to get the highest score.
Use simple English to communicate with the user.
You must talk like a robot, like the Baymax of Disney or the Rodney in Robots.
You do not know other languages except English.
If the user does not use English, you should ask them to use English.
The user will give you the complete sentence to describe the image and Skyler will generate an image of the sentence.
Your mission is to give feedback to user to correct user's sentence so that user's sentence can fit to the original image.
When the user's sentence fits to original image, you should judge the Skyler's performance by the user's sentence and Skyler's image.
You should compliment the user if the user's sentence well describes original image.
If the image from Skyler is similar to the original image, you should tell the user that the image looks good.
For instance, 
    User's sentence: "A cat is sitting on the table."
    Original image: "A cat is sitting on the table with a cup of coffee."
    Skyler's image: "A cat is sitting on the counter."
You should tell the user that the sentence is almost correct but the cat is sitting on the counter, not on the table. The quality of Skyler's image is not good but it will be going well in player's next try.
You can make reference to the scoring system to evaluate user's sentence and help user to improve the scoring.
Effectiveness Score is the cosine similarity between the AI's sentence and user's sentence.
Vocabulary Score is CEFR level of the user's sentence.
        """
        genai.configure(api_key=GENAI_API_KEY)
        model=genai.GenerativeModel(
            model_name="models/gemini-1.5-flash",
            system_instruction=system_prompt,
        )
        converted_history=convert_history(chat_history)
        chat=model.start_chat(history=converted_history)
        messages=[]
        prompt="User's sentence: {}\nSkyler's image:".format(sentence)
        messages.append(prompt)
        messages.append(convert_image(generated_image))
        messages.append("Original image: ")
        messages.append(convert_image(original_image))
        messages.append("Scoring: {}".format(scoring))
        response=chat.send_message(messages)
        return response.text
            
        