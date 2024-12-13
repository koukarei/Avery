import gradio as gr

import io
import requests
import base64
import PIL.Image
from PIL.PngImagePlugin import PngImageFile
from PIL.JpegImagePlugin import JpegImageFile
import os
import datetime

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

class Guidance:
    """"Create a guidance object for the user interface."""

    def create_guidance(self):
        with gr.Column(elem_classes="guidance"):
            with gr.Row():
                self.chat=gr.Chatbot(
                    value=None,
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

            
        