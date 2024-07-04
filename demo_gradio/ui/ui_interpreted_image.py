import gradio as gr

class InterpretedImage:
    def __init__(self):
        self.image=None
        self.interpreted_image=None
        self.submit_btn=None

    def create_interpreted_image(self,image,sentence:str):
        self.image=gr.Image(value=image,label='Image', interactive=False)
        from function.gen_image import gen_image
        image_url=gen_image(sentence)
        self.interpreted_image=gr.Image(value=image_url,label='Interpreted Image', interactive=False)
        
        self.submit_btn=gr.Button("Recover Avery",scale=0)