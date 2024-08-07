import gradio as gr
from typing import List, Dict

from dependencies.round import Round

from ui.ui_init import Guidance
from ui.ui_gallery import Gallery
from ui.ui_sentence import Sentence
from ui.ui_interpreted_image import InterpretedImage
from ui.ui_result import Result

testing=False

step_list_start= [
    {"name":"Select/Upload Image","Interactive":True},
    {"name":"Sentence","Interactive":False},
    {"name":"Verify","Interactive":False},
    {"name":"Results","Interactive":False},
    #{"name":"Leaderboard","Interactive":False},
    ]

def initialize_steps():
    return step_list_start.copy()
def initialize_cur_step():
    return 0

with gr.Blocks() as demo:
    round=Round()
    gallery=Gallery()
    sentence=Sentence()
    interpreted_image=InterpretedImage()
    result=Result()
    round.cur_step=gr.State(initialize_cur_step())
    steps=gr.State(initialize_steps())
    guidance=Guidance()
    with gr.Row(equal_height=True,show_progress=True,elem_classes='whole'):
        with gr.Column(min_width=200,elem_classes='bot'):
            if guidance.history:
                guidance.create_guidance(greeting=False)
            else:
                guidance.create_guidance(greeting=True)

        @gr.render(inputs=steps)
        def render_steps(step_list: List[Dict[str, bool]]):
            with gr.Column(min_width=300,elem_classes='interactive'):
                for step in step_list:
                    with gr.Tab(step['name'],interactive=step['Interactive']):
                        if step['name']=="Select/Upload Image" and step['Interactive']:
                            round.reset()
                            guidance.reset()
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
                                
                                else:
                                    gr.Warning("Please check the sentence.")
                                return step_list
                            
                            gr.on(triggers=[sentence.submit_btn.click],fn=verify_page,inputs=[steps],outputs=[steps])

                        elif step['name']=="Verify" and step['Interactive']:
                            interpreted_image.create_interpreted_image(sentence.image.value['path'],sentence.checked_value)
                            
                            def scoring_page(step_list):
                                if interpreted_image.submit_btn.click:
                                    for step in step_list:
                                        step['Interactive'] = False
                                    step_list[3]['Interactive'] = True
                                    result.get_params(round)
                                    scoring="Effectiveness score: {}\nVocabulary score: {}".format(
                                        round.effectiveness_score,
                                        round.vocab_score
                                    )
                                    guidance.set_interpreted_image(
                                        sentence=sentence.checked_value,
                                        interpreted_image=interpreted_image.interpreted_img_content,
                                        scoring=scoring
                                    )
                                    return step_list,guidance.history
                            interpreted_image.submit_btn.click(scoring_page,inputs=[steps],outputs=[steps,guidance.chat])
                        elif step['name']=="Results" and step['Interactive']:
                            result.create_result_tab()
                            round.set_interpreted_picture(interpreted_image.interpreted_img_content)
                            round.set_chat_history(guidance.history)
                            
                            result.save_image()
                            result.log_result()

                            def restart(step_list):
                                for step in step_list:
                                    step['Interactive'] = False
                                step_list[0]['Interactive'] = True
                                guidance.chat.value=[]
                                return step_list
                            
                            gr.on(triggers=[result.restart_btn.click],fn=restart,inputs=[steps],outputs=[steps])

                            
                        elif step['name']=="Leaderboard":
                            leaderboard=gr.Textbox(value='Release soon...?',interactive=False)
            
if __name__ == "__main__":
    demo.launch(share=False,server_name="0.0.0.0",server_port=7860)
    