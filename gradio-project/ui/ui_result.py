import gradio as gr

class Result:
    def __init__(self):
        self.image=None
        self.similarity=None
        self.ai_image=None
        self.restart_btn=None
        self.end_btn=None


    def create_result(self):
        self.similarity=gr.Markdown("Similarity")
        with gr.Row():
            self.image=gr.Image(None,label="Original",interactive=False)
            self.ai_image=gr.Image(None,label="Interpreted",interactive=False)
        
        with gr.Row():
            self.restart_btn=gr.Button("もう一回！",scale=0, link="/retry", visible=False)
            self.end_btn=gr.Button("やめる",scale=0,link='/new_game', visible=False)
