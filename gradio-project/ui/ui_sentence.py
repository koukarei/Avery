import gradio as gr

class Sentence:
    """Combine keywords into a sentence.
        Let AI to check the sentence.
    """

    def __init__(self):
        self.sentence=None
        self.check_btn=None
        self.checked_sentence=None
        self.submit_btn=None
        self.image=None

    def create_image(self,image):
        if isinstance(image,gr.components.Image):
            from PIL import Image as Im
            image=Im.fromarray(image.value)
        self.image=gr.Image(
            image,
            label="Type sentence to describe the image.",
            interactive=False,
        )

    def create_sentence(self,image_path):
        self.create_image(image_path)
        self.sentence=gr.Textbox(label='Your Sentence',interactive=True)
        self.check_btn=gr.Button("Check your sentence",scale=0)

        self.checked_sentence=gr.Textbox(label='Checked Sentence',interactive=False)
        
        self.submit_btn=gr.Button("Send to Skyler",scale=0)
        
    
