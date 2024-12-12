import gradio as gr
import os
from api.connection import read_leaderboard
import random

class Gallery:
    """Create a gallery object for the user interface."""

    def __init__(self, text_file_path="data/text_files"):
        self.text_file_path = text_file_path
        self.gallery = None
        self.image = None
        self.submit_btn = None
        self.selected=None
        self.ai_img=None
        self.transform_img=None
    
    def create_gallery(self):
        with gr.Column(elem_classes="gallery"):
            self.image = gr.Image(value=None, label="Original Picture", interactive=False, visible=False)
            # if testing:
            #     self.gallery = gr.Gallery(loop_files(), label="Original", interactive=True)
            # else:
            #     self.gallery = gr.Gallery(generate_images(self.text_file_path,round=round), label="Original", interactive=True)
            self.gallery = gr.Gallery(None, label="Original", interactive=False)
            self.submit_btn = gr.Button("Submit", scale=0)
            self.ai_img = gr.Image(value=None, label="AI Picture", interactive=False, visible=False)

        # Define event handlers
        self.gallery.upload(self.upload_picture, inputs=self.gallery, outputs=self.image)
        self.gallery.select(self.on_select, None, self.image)

    def upload_picture(self, image):
        return image[0][0]
    
    def on_select(self, evt: gr.SelectData):
        self.selected=evt.value['image']['path']
        return evt.value['image']['path']
        
