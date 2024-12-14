import gradio as gr

import io
import requests
import base64
import PIL.Image
from PIL.PngImagePlugin import PngImageFile
from PIL.JpegImagePlugin import JpegImageFile
import os
import datetime
import time

from api.connection import send_message, get_chat
from api import models

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



        