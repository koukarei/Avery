import gradio as gr
from typing import List

from ui.ui_gallery import Gallery
from ui.ui_keywords import Keywords
from ui.ui_sentence import Sentence
from ui.ui_interpreted_image import InterpretedImage
from ui.ui_result import Result

testing=False

step_list= [
    {"name":"Select/Upload Image","Interactive":False},
    {"name":"Type keywords","Interactive":False},
    {"name":"Sentence","Interactive":False},
    {"name":"Verify","Interactive":False},
    {"name":"Results","Interactive":False},
    {"name":"Leaderboard","Interactive":False},
    ]

with gr.Blocks() as demo:

    steps=gr.State([])
    gallery=Gallery()
    keywords=Keywords()
    sentence=Sentence()
    interpreted_image=InterpretedImage()
    result=Result()
    with gr.Row():
        with gr.Column():
            from ui.ui_init import Guidance
            guidance=Guidance()
            guidance.create_guidance()

            @guidance.start_btn.click(inputs=[steps],outputs=[steps])
            def start(step_list): 
                step_list=globals()['step_list']
                step_list[0]['Interactive'] = True
                return step_list

        with gr.Column():
            @gr.render(inputs=steps)
            def render_steps(step_list):
                step_list=globals()['step_list'].copy()
                for step in step_list:
                    with gr.Tab(step['name'],interactive=step['Interactive']):
                        if step['name']=="Select/Upload Image":
                            
                            gallery.create_gallery()
                            
                            def submit_image(step_list):
                                if gallery.image:
                                    step_list[0]['Interactive'] = False
                                    step_list[1]['Interactive'] = True

                                    #ai_image=result.ssim_ai_behavior(gallery.selected)
                                    return step_list
                                else:
                                    gr.Warning("Please select an image.")
                            
                            gr.on(triggers=[gallery.submit_btn.click],fn=submit_image,inputs=[steps],outputs=[steps])
                        elif step['name']=="Type keywords" and step['Interactive']:
                            
                            keywords.create_keyword_tab(gallery.selected,testing)
                            
                            def submit_keywords(step_list):
                                step_list[0]['Interactive'] = False
                                step_list[1]['Interactive'] = False
                                step_list[2]['Interactive'] = True
                                return step_list
                            
                            gr.on(triggers=[keywords.submit_btn.click],fn=submit_keywords,inputs=[steps],outputs=[steps])

                        elif step['name']=="Sentence":
                            sentence.create_sentence()
                            if testing:
                                sentence.sentence.value="A cat with brown collar and long whiskers was shocked."
                            def verify_page(step_list,keyword_list):
                                keywords.keyword_list=keyword_list
                                if sentence.checked_value:
                                    step_list[0]['Interactive'] = False
                                    step_list[1]['Interactive'] = False
                                    step_list[2]['Interactive'] = False
                                    step_list[3]['Interactive'] = True
                                    return step_list,[]
                                    
                                else:
                                    gr.Warning("Please check the sentence.")
                            
                            gr.on(triggers=[sentence.submit_btn.click],fn=verify_page,inputs=[steps,keywords.keywords],outputs=[steps,keywords.keywords])

                        elif step['name']=="Verify" and step['Interactive']:
                            interpreted_image.create_interpreted_image(keywords.image.value['path'],sentence.checked_value)
                            def scoring_page(step_list):
                                if interpreted_image.submit_btn.click:
                                    step_list[0]['Interactive'] = False
                                    step_list[1]['Interactive'] = False
                                    step_list[2]['Interactive'] = False
                                    step_list[3]['Interactive'] = False
                                    step_list[4]['Interactive'] = True
                                    return step_list
                            interpreted_image.submit_btn.click(scoring_page,inputs=[steps],outputs=[steps])
                        elif step['name']=="Results" and step['Interactive']:
                            leaderboard=gr.Textbox(value='Release soon...?',interactive=False)
                            # result.create_result(
                            #     original_img=gallery.selected,
                            #     checked_img=interpreted_image.image.value['path'],
                            #     keywords=keywords.keyword_list,
                            #     original_sentence=sentence.original_sentence,
                            #     checked_sentence=sentence.checked_value
                            # )
                            result.leaderboard_btn=gr.Button("Leaderboard",scale=0)
                            def go_leaderboard(step_list):
                                step_list[0]['Interactive'] = False
                                step_list[1]['Interactive'] = False
                                step_list[2]['Interactive'] = False
                                step_list[3]['Interactive'] = False
                                step_list[4]['Interactive'] = False
                                step_list[5]['Interactive'] = True
                                return step_list
                            
                            gr.on(triggers=[result.leaderboard_btn.click],fn=go_leaderboard,inputs=[steps],outputs=[steps])
                        elif step['name']=="Leaderboard":
                            leaderboard=gr.Textbox(value='Release soon...?',interactive=False)

            @gr.render(inputs=[keywords.keywords])
            def render_keywords(keyword_list):
                keywords.render_keywords(keyword_list)

if __name__ == "__main__":
    demo.launch(share=not testing)
    