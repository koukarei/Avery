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
        try:
            pilImage = PIL.Image.open(io.BytesIO(requests.get(img).content))
        except:
            pilImage = PIL.Image.open(img)
        return pilImage
    return None

def convert_history(history):
    # raw history format=[[None, "Hello"], [None, "How are you?"]]
    # new converted history format=[
    #     {"parts": [{"text": "Hello"}]},
    #     {"parts": [{"text": "How are you?"}]}
    # ]
    converted_history = []
    for i in history:
        # Skip None messages
        if i[0] is not None:
            if isinstance(i[0], list):
                for j in i[0]:
                    if isinstance(j, str):
                        converted_history.append({
                            "role": "user",
                            "parts": [{"text": j}]
                        })
                    elif isinstance(j, PIL.Image.Image):
                        # Handle image object
                        buffered = io.BytesIO()
                        j.save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        converted_history.append({
                            "role": "user",
                            "parts": [{
                                "mime_type": "image/png", 
                                "data": img_str,
                            }]
                        })
                    elif isinstance(j, genlang_content.Content):
                        if j.parts.text:
                            converted_history.append({
                                "role": "user",
                                "parts": [{"text": part.text} for part in j.parts if part.text]
                            })
                        elif j.parts.inline_data:
                            converted_history.append({
                                "role": "user",
                                "inline_data": {"mime_type": j.parts.mime_type, "data": j.parts.inline_data.data}
                            })
                        converted_history.append(j)
                    else:
                        if j.parts.text:
                            converted_history.append({"role":"user","parts": [{"text": part.text} for part in j.parts if part.text]})
                        elif j.parts.inline_data:
                            converted_history.append({"inline_data": {"mime_type": j.parts.mime_type, "data": j.parts.inline_data.data}})
                        converted_history.append(j)
            else:
                converted_history.append({"parts": [{"text": i[0]}]})
        if i[1] is not None:
            converted_history.append({
                "role": "model",
                "parts": [{"text": i[1]}]
            })
    return converted_history

class Hint_Chatbot:
    def __init__(self,greetingmsg):
        genai.configure(api_key=GENAI_API_KEY)
        self.chat_history=[[None,greetingmsg]]
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
        self.chat=model.start_chat(history=[])
        self.original_image=None

    def add_image(self, img,story):
        messages=[]
        messages.append(story)
        if img:
            self.original_image=img
            if isinstance(img, list):
                for i in img:
                    pilImage = convert_image(i)
                    messages.append(pilImage)
            else:
                pilImage = convert_image(img)
                messages.append(pilImage)
            response=self.chat.send_message(messages)
            self.chat_history.append([messages,response.text])
            return response.text
        return ''
    
    def nextResponse(self, ask_for_hint):
        messages=[]
        messages.append(ask_for_hint)

        if len(messages)==0:
            print("No messages")
            return {}

        try:
            response=self.chat.send_message(messages)
            self.chat_history.append([messages,response.text])
            return response.text
        except Exception as e:
            print(f"Error: {e}")
            print(f"Messages: {messages}")
            return {}
        

    def get_result(self,generated_image, sentence,scoring):
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
        converted_history=convert_history(self.chat_history)
        chat=model.start_chat(history=converted_history)
        messages=[]
        prompt="User's sentence: {}\nSkyler's image:".format(sentence)
        messages.append(prompt)
        messages.append(convert_image(generated_image))
        messages.append("Original image: ")
        messages.append(convert_image(self.original_image))
        messages.append("Scoring: {}".format(scoring))
        response=chat.send_message(messages)
        return response.text

class Guidance:
    """"Create a guidance object for the user interface."""
    def __init__(self):
        self.greetingmsg="""
            Greetings, human. 🤖 I am Avery the Robot. 📸

            Let's try to select an image and get the best scoring! 🛠️

            1. Select image. 🖼️
            2. Use complete sentence to describe the image. 🗣️
            3. Skyler the Robot will process and generate an image based on your sentence. Verify its output. ✅
            4. Your sentences will be scored by relevance, vocabulary and grammar. 📊
            """
        self.chatbot=Hint_Chatbot(greetingmsg=self.greetingmsg)
        self.history=[]

    def create_guidance(self,greeting=False):
        
        with gr.Column(elem_classes="guidance"):
            with gr.Row():
                if greeting:
                    self.history.append([None,self.greetingmsg])

                self.chat=gr.Chatbot(
                    value=self.history,
                    label="Chat with Avery",
                    show_copy_button=True,
                    elem_classes="chat",
                    height="600px"
                )

            with gr.Row():
                with gr.Column(scale=2,min_width=200):
                    self.msg=gr.Textbox(placeholder="Type your message to Avery here.",label="Your message to Avery 🤖")
                    self.msg.submit(self.slow_echo,[self.msg,self.chat],[self.msg,self.chat])
                with gr.Column(scale=1,min_width=80):
                    self.submit=gr.Button("Ask Avery for hint")
                    self.submit.click(self.slow_echo,[self.msg,self.chat],[self.msg,self.chat])

    def reset(self):
        self.chatbot=Hint_Chatbot(greetingmsg=self.greetingmsg)
        
    def set_image(self, img,story):
        response=self.chatbot.add_image(img,story)
        if response:
            self.history.append([None,"The image is imported to my system. You can ask me for a hint."])
        else:
            self.history.append([None,"No image is imported to my system, human."])
        return self.history

    def set_sentence(self, sentence):
        new_message="""
We input the sentence into Skyler's system. 📝
Sentence: {}
""".format(sentence)
        self.history.append([None,new_message])
        return self.history

    def set_interpreted_image(self,sentence,interpreted_image,scoring):
        response=self.chatbot.get_result(interpreted_image,sentence,scoring)
        self.history.append([None,response])
        return self.history

    def slow_echo(self,message, history):
        if self.chatbot.original_image is None:
            history.append((message, "No image is imported to my system, human.\nI cannot provide you with a hint."))
            self.history=history
            return "", history
        else:
            hint=self.chatbot.nextResponse(message)
            history.append((message, hint))
            self.history=history
            return "", history
            
        