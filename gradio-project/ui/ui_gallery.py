import gradio as gr
import os

def loop_files(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            yield file_path

class Gallery:
    """Create a gallery object for the user interface."""

    def __init__(self, image_path="data/Public picture"):
        self.image_path = image_path
        self.gallery = None
        self.image = None
        self.submit_btn = None
        self.selected=None
        self.ai_img=None
    
    def create_gallery(self):
        with gr.Column(elem_classes="gallery"):
            self.image = gr.Image(value=None, label="Original Picture", interactive=False, visible=False)
            self.gallery = gr.Gallery(loop_files(self.image_path), label="Original", interactive=True)
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
        
    def hide_gallery(self):
        self.gallery.visible=False
        self.submit_btn.visible=False

    def show_gallery(self):
        self.gallery.visible=True
        self.submit_btn.visible=True

    def get_selected_image(self):
        self.image.visible=True
        return self.image

    def remove_selected_image(self):
        self.image.visible=False
        return self.image
