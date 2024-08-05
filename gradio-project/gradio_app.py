import gradio as gr
from typing import List, Dict

from dependencies.round import Round

from ui.ui_gallery import Gallery
from ui.ui_sentence import Sentence
from ui.ui_interpreted_image import InterpretedImage
from ui.ui_result import Result

testing=False

gallery=Gallery()
sentence=Sentence()
interpreted_image=InterpretedImage()
result=Result()

step_list_start= [
    {"name":"Select/Upload Image","Interactive":True},
    {"name":"Sentence","Interactive":False},
    {"name":"Verify","Interactive":False},
    {"name":"Results","Interactive":False},
    #{"name":"Leaderboard","Interactive":False},
    ]

def initialize_steps():
    return step_list_start.copy()

with gr.Blocks() as demo:
    round=Round()
    steps=gr.State(initialize_steps())
    
    with gr.Row():
        with gr.Column():
            from ui.ui_init import Guidance
            guidance=Guidance()
            guidance.create_guidance()

        with gr.Column():
            @gr.render(inputs=steps)
            def render_steps(step_list: List[Dict[str, bool]]):
                for step in step_list:
                    with gr.Tab(step['name'],interactive=step['Interactive']):
                        if step['name']=="Select/Upload Image" and step['Interactive']:
                            gallery.create_gallery(round=round)
                            def submit_image(step_list):
                                if gallery.image:
                                    step_list=step_list_start.copy()
                                    for step in step_list:
                                        step['Interactive'] = False
                                    step_list[1]['Interactive'] = True
                                    chat_history=guidance.set_image(gallery.selected)
                                    round.set_original_picture(gallery.selected)
                                    return step_list,chat_history
                                else:
                                    gr.Warning("Please select an image.")
                                round.reset()
                            gr.on(triggers=[gallery.submit_btn.click],fn=submit_image,inputs=[steps],outputs=[steps,guidance.chat])
                        elif step['name']=="Sentence" and step['Interactive']:

                            sentence.create_sentence(gallery.selected)
                            def verify_page(step_list):
                                
                                if sentence.checked_value:
                                    for step in step_list:
                                        step['Interactive'] = False
                                    step_list[2]['Interactive'] = True
                                    round.set_sentence(
                                        sentence=sentence.original_sentence,
                                        corrected_sentence=sentence.checked_value
                                    )
                                    return step_list
                                
                                else:
                                    gr.Warning("Please check the sentence.")
                            
                            gr.on(triggers=[sentence.submit_btn.click],fn=verify_page,inputs=[steps],outputs=[steps])

                        elif step['name']=="Verify" and step['Interactive']:
                            interpreted_image.create_interpreted_image(sentence.image.value['path'],sentence.checked_value)
                            
                            new_chat=guidance.set_interpreted_image(
                                sentence=sentence.checked_value,
                                interpreted_image=interpreted_image.interpreted_img_content
                            )
                            def scoring_page(step_list):
                                if interpreted_image.submit_btn.click:
                                    for step in step_list:
                                        step['Interactive'] = False
                                    step_list[3]['Interactive'] = True
                                    round.set_interpreted_picture(interpreted_image.interpreted_img_content)
                                    round.set_chat_history(guidance.chat.value)
                                    return step_list,new_chat
                            interpreted_image.submit_btn.click(scoring_page,inputs=[steps],outputs=[steps,guidance.chat])
                        elif step['name']=="Results" and step['Interactive']:
                            result.get_params(round)
                            result.create_result_tab()
                            result.save_image()
                            result.log_result()

                            def restart(step_list):
                                for step in step_list:
                                    step['Interactive'] = False
                                step_list[0]['Interactive'] = True
                                return step_list
                            
                            gr.on(triggers=[result.restart_btn.click],fn=restart,inputs=[steps],outputs=[steps])
                        elif step['name']=="Leaderboard":
                            leaderboard=gr.Textbox(value='Release soon...?',interactive=False)
            
if __name__ == "__main__":
    demo.launch(share=not testing,server_name="0.0.0.0",server_port=7860)
    