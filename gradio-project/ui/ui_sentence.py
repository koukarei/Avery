import gradio as gr
from PIL import Image

class Sentence:
    """Combine keywords into a sentence.
        Let AI to check the sentence.
    """

    def __init__(self):
        self.sentence=None
        self.submit_btn=None
        self.image=None

    def create_sentence(self):
        self.image=gr.Image(
            None,
            label="英作文を入力してください",
            interactive=False,
        )
        self.sentence=gr.Textbox(label='英作文',interactive=True, max_length=180)

        self.submit_btn=gr.Button("送信",scale=0)
        
    
