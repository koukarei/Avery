import gradio as gr
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
from dotenv import load_dotenv
import datetime

# .envファイルの内容を読み込見込む
load_dotenv()

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
    # raw history format=[[None, "Hello"], [None, "How are you?"]]
    # new converted history format=[
    #     {"parts": [{"text": "Hello"}]},
    #     {"parts": [{"text": "How are you?"}]}
    # ]

    target = {
        "contents": [],
    }
    
    # Extract data from the original format
    for entry in original:
        if entry[0]:
            
            if isinstance(entry[0], str):  # Text entry
                role = "user"
                target["contents"].append({
                    "role": role,
                    "parts": [{
                        "text": entry[1]
                    }]
                })
            elif isinstance(entry[0], list):  # File entry
                mime_type = entry[0][0]
                file_uri = entry[0][1]
                target["contents"].append({
                    "role": "user",
                    "parts": [{
                        "fileData": {
                            "mimeType": mime_type,
                            "fileUri": file_uri
                        }
                    }]
                })
            elif isinstance(entry[0],PngImageFile):
                target["contents"].append({
                    "role": "user",
                    "parts": [{
                        "fileData": {
                            "mimeType": "image/png",
                            "fileUri": "data:image/png;base64," + base64.b64encode(io.BytesIO(entry[0]).read()).decode()
                        }
                    }]
                })
            elif isinstance(entry[0],JpegImageFile):  # Image entry
                target["contents"].append({
                    "role": "user",
                    "parts": [{
                        "fileData": {
                            "mimeType": "image/jpeg",
                            "fileUri": "data:image/jpeg;base64," + base64.b64encode(io.BytesIO(entry[0]).read()).decode()
                        }
                    }]
                })
            else:
                raise ValueError("Unknown entry type")
        
        if entry[1]:
            target["contents"].append({
                "role": "model",
                "parts": [{
                    "text": entry[1]
                }]
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
You must talk like a robot, like the Baymax of Disney or the Rodney in Robots.
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

    def add_image(self, img,story,chat_history):
        chat=self.model.start_chat(history=convert_history(chat_history))
        messages=[]
        messages.append(story)
        #messages.append({'role':'user','Content':{'parts':[{'text':story}]}})
        if img:
            
            if isinstance(img, list):
                for i in img:
                    pilImage = convert_image(i)
                    messages.append(pilImage)
            else:
                pilImage = convert_image(img)
                messages.append(pilImage)
            response=chat.send_message(messages)
            return response.text
        return ''
    
    def nextResponse(self, ask_for_hint,chat_history,original_image):
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

class Guidance:
    """"Create a guidance object for the user interface."""
    def __init__(self):
        self.chatbot=Hint_Chatbot()

    def create_guidance(self,chat_history):
        
        with gr.Column(elem_classes="guidance"):
            with gr.Row():
                self.chat=gr.Chatbot(
                    value=chat_history,
                    label="Chat with Avery",
                    show_copy_button=True,
                    elem_classes="chat",
                    height="600px"
                )

            with gr.Row():
                with gr.Column(scale=2,min_width=200):
                    self.msg=gr.Textbox(placeholder="Type your message to Avery here.",label="Your message to Avery 🤖")
                    
                with gr.Column(scale=1,min_width=80):
                    self.submit=gr.Button("Ask Avery for hint")
                  

    def reset(self):
        self.chatbot=Hint_Chatbot()
        
    def set_image(self, img,story,chat_history):
        response=self.chatbot.add_image(img,story,chat_history)
        if response:
            chat_history.append([None,"The image is imported to my system. You can ask me for a hint."])
        else:
            chat_history.append([None,"No image is imported to my system, human."])
        self.chat.value=chat_history
        return chat_history

    def set_sentence(self, sentence,chat_history):
        new_message="""
We input the sentence into Skyler's system. 📝
Sentence: {}
""".format(sentence)
        chat_history.append([None,new_message])
        return chat_history

    def set_interpreted_image(self,sentence,interpreted_image,scoring,original_image,chat_history):
        response=self.chatbot.get_result(interpreted_image,sentence,scoring,original_image,chat_history)
        chat_history.append([None,response])
        return chat_history

    def slow_echo(self,message, history,game_data):
        if game_data['original_picture'] is None:
            new=[message,"No image is imported to my system, human.\nI cannot provide you with a hint."]
            history.append(new)
            game_data['chat_history'].append(new)
            
        elif message is not None:
            hint=self.chatbot.nextResponse(message,history,game_data['original_picture'])
            history.append((message, hint))
            game_data['chat_history'].append((message, hint))
        return "", history,game_data
            
        