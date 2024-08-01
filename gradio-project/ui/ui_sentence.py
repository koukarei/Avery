import gradio as gr

class Sentence:
    """Combine keywords into a sentence.
        Let AI to check the sentence.
    """

    def __init__(self):
        self.original_sentence=None
        self.sentence=None
        self.check_btn=None
        self.checked_sentence=None
        self.submit_btn=None
        self.checked_value=None
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
        self.sentence=gr.Textbox(label='Sentence',interactive=True)
        self.check_btn=gr.Button("Check",scale=0)

        self.checked_sentence=gr.Textbox(label='Checked Sentence',interactive=False)

        def check_sentence(sentence):
            if sentence:
                from function.sentence import checkSentence
                self.original_sentence=sentence
                self.checked_value=checkSentence(sentence)
                return self.checked_value
            else:
                gr.Warning("Please type a sentence.")
        self.check_btn.click(check_sentence,[self.sentence],[self.checked_sentence])
        self.submit_btn=gr.Button("Get Interpretation",scale=0)
        
    
