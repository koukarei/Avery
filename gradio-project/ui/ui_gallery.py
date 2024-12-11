import gradio as gr
import os
from ..api.connection import read_leaderboard
import random

def generate_images(directory,round:Round,n=1):
    files = os.listdir(directory)
    files = random.sample(files,n)
    contents=""
    for filename in files:
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            with open(file_path, "r") as txt_file:
                content=txt_file.read()
            contents+=content
    gen_image=GenerateOriginalImage(contents)
    images=gen_image.get_original_images(round)
    for image in images:
        yield image
            

def get_original_images(request: gr.Request):
    read_leaderboard(request.)

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
            self.gallery = gr.Gallery(loop_files(), label="Original", interactive=False)
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
        
