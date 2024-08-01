import gradio as gr
from typing import List

from ui.ui_gallery import Gallery
from ui.ui_keywords import Keywords
from ui.ui_sentence import Sentence
from ui.ui_interpreted_image import InterpretedImage
from ui.ui_result import Result

testing=True
init=True


with gr.Blocks() as demo:
    step_list_start= [
        {"name":"Select/Upload Image","Interactive":False},
        {"name":"Sentence","Interactive":False},
        {"name":"Verify","Interactive":False},
        {"name":"Results","Interactive":False},
        #{"name":"Leaderboard","Interactive":False},
        ]

    steps=gr.State([])

    steps.value=step_list_start

    gallery=Gallery()
    sentence=Sentence()
    interpreted_image=InterpretedImage()
    result=Result()
    with gr.Row():
        with gr.Column():
            from ui.ui_init import Guidance
            guidance=Guidance()
            guidance.create_guidance()

            step_list=step_list_start.copy()
            for step in step_list:
                step['Interactive'] = False
            step_list[0]['Interactive'] = True

        with gr.Column():
            @gr.render(inputs=steps)
            def render_steps(step_list):
                for step in step_list:
                    with gr.Tab(step['name'],interactive=step['Interactive']):
                        if step['name']=="Select/Upload Image" and step['Interactive']:
                            
                            gallery.create_gallery()
                            def submit_image(step_list):
                                if gallery.image:
                                    step_list=step_list_start.copy()
                                    for step in step_list:
                                        step['Interactive'] = False
                                    step_list[1]['Interactive'] = True
                                    print(gallery.selected)
                                    guidance.set_image(gallery.selected)
                                    
                                    return step_list
                                else:
                                    gr.Warning("Please select an image.")
                            
                            gr.on(triggers=[gallery.submit_btn.click],fn=submit_image,inputs=[steps],outputs=[steps])
                        elif step['name']=="Sentence" and step['Interactive']:
                            sentence.create_sentence(gallery.selected)
                            def verify_page(step_list):
                                
                                if sentence.checked_value:
                                    for step in step_list:
                                        step['Interactive'] = False
                                    step_list[2]['Interactive'] = True
                                    return step_list
                                
                                else:
                                    gr.Warning("Please check the sentence.")
                            
                            gr.on(triggers=[sentence.submit_btn.click],fn=verify_page,inputs=[steps],outputs=[steps])

                        elif step['name']=="Verify" and step['Interactive']:
                            interpreted_image.create_interpreted_image(sentence.image.value['path'],sentence.checked_value)
                            guidance.set_interpreted_image(
                                sentence=sentence.checked_value,
                                interpreted_image=interpreted_image.image.value['path']
                            )
                            def scoring_page(step_list):
                                if interpreted_image.submit_btn.click:
                                    for step in step_list:
                                        step['Interactive'] = False
                                    step_list[3]['Interactive'] = True
                                    return step_list
                            interpreted_image.submit_btn.click(scoring_page,inputs=[steps],outputs=[steps])
                        elif step['name']=="Results" and step['Interactive']:
                            
                            # result.create_result(
                            #     original_img=gallery.selected,
                            #     hint_history=guidance.history,
                            #     original_sentence=sentence.original_sentence,
                            #     checked_sentence=sentence.checked_value
                            # )

                            result.leaderboard_btn=gr.Button("Leaderboard",scale=0)
                            def go_leaderboard(step_list):
                                for step in step_list:
                                    step['Interactive'] = False
                                step_list[4]['Interactive'] = True
                                return step_list
                            
                            gr.on(triggers=[result.leaderboard_btn.click],fn=go_leaderboard,inputs=[steps],outputs=[steps])
                        elif step['name']=="Leaderboard":
                            leaderboard=gr.Textbox(value='Release soon...?',interactive=False)
            
if __name__ == "__main__":
    demo.launch(share=not testing,server_name="0.0.0.0",server_port=7860)
    