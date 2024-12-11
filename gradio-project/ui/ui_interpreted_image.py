import gradio as gr
from PIL import Image
import requests
import io

class InterpretedImage:
    def __init__(self):
        self.image=None
        self.interpreted_image=None
        self.submit_btn=None

    def set_sentence(self,sentence:str):
        self.sentence=sentence

    def create_interpreted_image(self,image,sentence:str):
        if sentence is None:
            gr.Info("Please enter a sentence.")
            return None
        self.image=gr.Image(value=image,label='Image', interactive=False)
        from function.gen_image import generate_interpretion
        image_url=generate_interpretion(sentence)
        self.interpreted_img_content=Image.open(io.BytesIO(requests.get(image_url).content))
        self.interpreted_image=gr.Image(value=self.interpreted_img_content,label='Interpreted Image', interactive=False)
        with gr.Row():
            self.regen_btn=gr.Button("Regenerate image",scale=0)
            @self.regen_btn.click(outputs=[self.interpreted_image])
            def regenerate_image():
                image_url=generate_interpretion(sentence)
                return image_url
            self.submit_btn=gr.Button("Recover Skyler",scale=0)