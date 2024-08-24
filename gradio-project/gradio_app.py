import gradio as gr
from typing import List, Dict

from dependencies.round import Round

from ui.ui_init import Guidance
from ui.ui_gallery import Gallery
from ui.ui_sentence import Sentence
from ui.ui_interpreted_image import InterpretedImage
from ui.ui_result import Result

testing=False

with gr.Blocks() as demo:

    step_list_start= [
        {"name":"Select/Upload Image","Interactive":True},
        {"name":"Sentence","Interactive":False},
        {"name":"Verify","Interactive":False},
        {"name":"Results","Interactive":False},
        #{"name":"Leaderboard","Interactive":False},
        ]
    initial_data={
        "round_id":None,
        "original_picture_path":None,
        "original_picture":None,
        "interpreted_picture":None,
        "story":None,
        "sentence":None,
        "corrected_sentence":None,
        "ai_play":None,
        "is_draft":True,
        "phrases":None,
        "semantic_score":None,
        "vocab_score":None,
        "effectiveness_score":None,
        "total":None,
        "rank":None,
        "chat_history":[]
    }
    def initialize_steps():
        return step_list_start.copy()
    
    round=Round()
    def initialize_data(rd:Round,chat_history=None):
        greetingmsg="""
Greetings, human. 🤖 I am Avery the Robot. 📸

Let's try to select an image and get the best scoring! 🛠️

1. Select image. 🖼️
2. Use complete sentence to describe the image. 🗣️
3. Skyler the Robot will process and generate an image based on your sentence. Verify its output. ✅
4. Your sentences will be scored by relevance, vocabulary and grammar. 📊
"""
        if chat_history:
            initial_data["chat_history"]=chat_history
        else:
            initial_data["chat_history"]=[[None,greetingmsg]]
        initial_data["round_id"]=rd.set_id()
        return initial_data.copy()
    cur_round=Round()
    gallery=Gallery()
    sentence=Sentence()
    interpreted_image=InterpretedImage()
    result=Result()
    
    game_data=gr.State(initialize_data(cur_round))
    steps=gr.State(initialize_steps())
    guidance=Guidance()
    with gr.Row(equal_height=True,show_progress=True,elem_classes='whole'):
        with gr.Column(min_width=200,elem_classes='bot'):
            guidance.create_guidance(chat_history=game_data.value['chat_history'])
            gr.on(triggers=[guidance.msg.submit,guidance.submit.click],
                  fn=guidance.slow_echo,
                  inputs=[guidance.msg,guidance.chat,game_data],
                  outputs=[guidance.msg,guidance.chat,game_data])

        @gr.render(inputs=steps)
        def render_steps(step_list: List[Dict[str, bool]]):
            with gr.Column(min_width=300,elem_classes='interactive'):
                for step in step_list:
                    with gr.Tab(step['name'],interactive=step['Interactive']):
                        if step['name']=="Select/Upload Image" and step['Interactive']:
                            gallery.create_gallery()
                            def submit_image(step_list,game_data_dict):
                                if gallery.image:
                                    step_list=step_list_start.copy()
                                    for step in step_list:
                                        step['Interactive'] = False
                                    step_list[1]['Interactive'] = True
                                    
                                    game_data_dict['original_picture_path'],game_data_dict['original_picture'],game_data_dict['story']=round.set_original_picture(gallery.selected)
                                    game_data_dict['chat_history']=guidance.set_image(game_data_dict['original_picture'],game_data_dict['story'],game_data_dict['chat_history'])
                                    
                                    return step_list,game_data_dict['chat_history'],game_data_dict
                                else:
                                    gr.Warning("Please select an image.")
                                    return step_list,game_data_dict['chat_history'],game_data_dict
                            gr.on(triggers=[gallery.submit_btn.click],fn=submit_image,inputs=[steps,game_data],outputs=[steps,guidance.chat,game_data],concurrency_limit=1)
                        elif step['name']=="Sentence" and step['Interactive']:
                            sentence.create_sentence(gallery.selected)
                            def check_sentence(sentence,game_data_dict):
                                if sentence:
                                    from function.sentence import checkSentence
                                    checked_value=checkSentence(sentence)
                                    if checked_value== "Please enter an English sentence.":
                                        gr.Info("Please enter an English sentence.")
                                    elif checked_value== "Please enter a valid English sentence.":
                                        gr.Info("Please enter a valid English sentence.")
                                    elif checked_value== "Please avoid offensive language.":
                                        gr.Info("Please avoid offensive language.")
                                    else:
                                        game_data_dict['sentence']=sentence
                                        game_data_dict['corrected_sentence']=checked_value
                                        return checked_value,game_data_dict
                                else:
                                    gr.Warning("Please type a sentence.")
                                return "",game_data_dict
                            sentence.check_btn.click(fn=check_sentence,inputs=[sentence.sentence,game_data],outputs=[sentence.checked_sentence,game_data])

                            def verify_page(step_list,game_data_dict):
                                
                                if game_data_dict['corrected_sentence'] is not None:
                                    for step in step_list:
                                        step['Interactive'] = False
                                    step_list[2]['Interactive'] = True
                                    game_data_dict['chat_history']=guidance.set_sentence(
                                        sentence=game_data_dict['corrected_sentence'],
                                        chat_history=game_data_dict['chat_history']
                                    )
                                    interpreted_image.set_sentence(game_data_dict['corrected_sentence'])
                                else:
                                    gr.Warning("Please check the sentence.")
                                return step_list,game_data_dict['chat_history'],game_data_dict
                            gr.on(triggers=[sentence.submit_btn.click],fn=verify_page,inputs=[steps,game_data],outputs=[steps,guidance.chat,game_data],concurrency_limit=1)
                            
                        elif step['name']=="Verify" and step['Interactive']:
                            interpreted_image.create_interpreted_image(sentence.image.value['path'],interpreted_image.sentence)
                            
                            def scoring_page(step_list,game_data_dict):
                                if interpreted_image.submit_btn.click:
                                    for step in step_list:
                                        step['Interactive'] = False
                                    step_list[3]['Interactive'] = True
                                    result.get_params(cur_round,game_data_dict)
                                    scoring="Effectiveness score: {}\nVocabulary score: {}".format(
                                        game_data_dict['effectiveness_score'],
                                        game_data_dict['vocab_score']
                                    )
                                    game_data_dict['interpreted_picture']=cur_round.set_interpreted_picture(interpreted_image.interpreted_img_content)
                                    game_data_dict['chat_history']=guidance.set_interpreted_image(
                                                    sentence=game_data_dict['corrected_sentence'],
                                                    interpreted_image=game_data_dict['interpreted_picture'],
                                                    scoring=scoring,
                                                    chat_history=game_data_dict['chat_history'],
                                                    original_image=game_data_dict['original_picture']
                                                )
                                    game_data_dict=result.save_image(game_data_dict=game_data_dict,cur_round=cur_round)
                                    result.log_result(game_data_dict)
                                    game_data_dict['is_draft']=False
                                    return step_list,game_data_dict['chat_history'],game_data_dict
                            gr.on(triggers=[interpreted_image.submit_btn.click],fn=scoring_page,inputs=[steps,game_data],outputs=[steps,guidance.chat,game_data],concurrency_limit=1)
                        elif step['name']=="Results" and step['Interactive']:
                            result.create_result_tab()

                            def restart(step_list,game_data_dict):
                                for step in step_list:
                                    step['Interactive'] = False
                                step_list[0]['Interactive'] = True
                                game_data_dict=initialize_data(cur_round,chat_history=game_data_dict['chat_history'])
                                return step_list,game_data_dict
                            
                            gr.on(triggers=[result.restart_btn.click],fn=restart,inputs=[steps,game_data],outputs=[steps,game_data],concurrency_limit=1)

                            
                        elif step['name']=="Leaderboard":
                            leaderboard=gr.Textbox(value='Release soon...?',interactive=False)
            
if __name__ == "__main__":
    demo.launch(share=True,server_name="0.0.0.0",server_port=7860)
    