import gradio as gr
import google.generativeai as genai
# https://ai.google.dev/api/python/google/generativeai/GenerativeModel?_gl=1*7pk6lc*_up*MQ..*_ga*NzQwNTA2OTc0LjE3MjA1MDg0Mzc.*_ga_P1DBVKWT6V*MTcyMDUwODQzNi4xLjAuMTcyMDUwODQzNi4wLjAuMTI4MjQwOTIyMQ..
# 必要モジュールのインポート
import io
import requests
import base64
import PIL.Image
import os
from dotenv import load_dotenv
import datetime

# .envファイルの内容を読み込見込む
load_dotenv()

# os.environを用いて環境変数を表示させます
GENAI_API_KEY=os.environ['GEMINI_API_KEY']

class Hint_Chatbot:
    def __init__(self):
        genai.configure(api_key=GENAI_API_KEY)

        system_prompt = f"""
        Your name is Avery. 
        You are a robot. 
        Your friend, Skyler, is damaged.
        You are cooperating with a human to repair Skyler.
        You need assistance to describe the image contents. 
        Skyler will get repaired if you can describe the image contents correctly.
        Use simple English to communicate with the user.
        The user will ask you hint to describe the image. 
        You should give the minimum hint to them with uncertain tone.
        You must talk like a robot.
        You do not other languages except English.
        If the user does not use English, you should ask them to use English.
        Finally, the user will give you the complete sentence to describe the image and Skyler will generate an image of the sentence.
        You should verify the sentence and image and give feedback to the user.
        You should compliment the user by telling them the recovery of Skyler and be grateful.
        If the image from Skyler is similar to the original image, you should tell the user that the recovery is well-going.
        """

        generation_config = {
            "max_tokens": 100,
            "temperature": 0.5,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "stop_sequence": "\n",
        }
        model=genai.GenerativeModel(
            model_name="models/gemini-1.5-flash",
            system_instruction=system_prompt,
            # generation_config=generation_config
        )

        self.model=model
        self.chat=model.start_chat(history=[])

    def add_image(self, img):
        messages=[]
        if img:
            if isinstance(img, list):
                for i in img:
                    pilImage = PIL.Image.open(io.BytesIO(requests.get(i).content))
                    messages.append(pilImage)
            else:
                pilImage = PIL.Image.open(io.BytesIO(requests.get(img).content))
                messages.append(pilImage)
            self.chat.send_message(messages)
            return
    
    def nextResponse(self, ask_for_hint):
        messages=[]
        messages.append(ask_for_hint)

        if len(messages)==0:
            print("No messages")
            return {}

        try:
            response=self.chat.send_message(messages)
            return response.text
        except Exception as e:
            print(f"Error: {e}")
            print(f"Messages: {messages}")
            return {}

    def interpretion(self, sentence, image):
        messages=[]
        messages.append(sentence)
        image=PIL.Image.open(io.BytesIO(requests.get(image).content))
        messages.append(image)

        if len(messages)==0:
            print("No messages")
            return {}

        try:
            response=self.chat.send_message(messages)
            return response.text
        except Exception as e:
            print(f"Error: {e}")
            print(f"Messages: {messages}")
            return {}

    def slow_echo(self,message, history):
        hint=self.nextResponse(message)
        history.append((message, hint))
        return "", history

class Guidance:
    """"Create a guidance object for the user interface."""

    guidance_box=None
    start_btn=None
    def create_guidance(self):
        self.chatbot=Hint_Chatbot()
        with gr.Column(elem_classes="guidance"):
            greetingmsg="""
                Greetings, human. 🤖 I am Robot Avery. 📸

                Camera malfunction detected. Assistance required. 🛠️

                1. Select image. 🖼️
                2. Use complete sentence to describe the image. 🗣️
                3. I will process and respond. Verify my output. ✅
                4. Contribution to system will be calculated. 📊
                """
            self.chat=gr.Chatbot(value=[[None,greetingmsg]])
            self.msg=gr.Textbox(placeholder="Type your message here.",label="Message")
            self.msg.submit(self.chatbot.slow_echo,[self.msg,self.chat],[self.msg,self.chat])

            self.submit=gr.Button("Submit")
            self.submit.click(self.chatbot.slow_echo,[self.msg,self.chat],[self.msg,self.chat])

    def set_image(self, img):
        self.chatbot.add_image(img)
        self.chat.value.append([None,"The image is imported to my system. You can ask me for a hint."])

    def set_interpreted_image(self,sentence,interpreted_image):
        response = self.chatbot.interpretion(sentence, interpreted_image)
        self.chat.value.append([None,response])

    def history(self):
        return self.chat.value

            
        