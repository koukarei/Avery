import gradio as gr

class Guidance:
    """"Create a guidance object for the user interface."""

    guidance_box=None
    start_btn=None
    def create_guidance(self):
        with gr.Column(elem_classes="guidance"):
            gr.Markdown("""
                Greetings, human. 🤖 I am Robot Avery. 📸

                Camera malfunction detected. Assistance required. 🛠️

                1. Upload image. 🖼️
                2. Describe image contents. 📝
                3. Use complete sentence. 🗣️
                4. I will process and respond. Verify my output. ✅
                5. Contribution to system will be calculated. 📊

                            """)
            
            self.start_btn=gr.Button("Start",elem_id="start_btn",scale=0)
        