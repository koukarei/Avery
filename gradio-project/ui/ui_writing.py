import gradio as gr
from PIL import Image

from ui.ui_chatbot import Guidance

import os
import datetime, zoneinfo

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from api.connection_2 import Play_Round_WS, get_interpreted_image, obtain_evaluation_from_past, get_generation
from api.connection import models

from ui.ui_gallery import app as fastapi_app

MAX_GENERATION = int(os.getenv("MAX_GENERATION", 5))

class Writing:
    """Combine keywords into a sentence.
        Let AI to check the sentence.
    """

    def __init__(self):
        self.sentence=None
        self.submit_btn=None
        self.image=None
        self.ai_images=None

    def create_original_image(self):
        self.image=gr.Image(
            None,
            label="英作文を入力してください",
            interactive=False,
        )

    def create_sentence(self):
        with gr.Column():
            with gr.Row():
                self.sentence=gr.Textbox(label='英作文',interactive=True, max_length=1000)

            with gr.Row():
                self.submit_btn=gr.Button("送信",scale=0)
                self.back_btn=gr.Button("戻る",scale=0, link="/avery/")

            with gr.Row():
                self.slider = gr.Slider(1,MAX_GENERATION,step=1, visible=False, label="英作文回数")

            with gr.Row():
                self.details = gr.Markdown(
                    visible=False,
                )

            with gr.Row():
                self.ai_image=gr.Image(
                    None,
                    label="AIが生成した画像",
                    interactive=False,
                    visible=False,
                )

                self.evaluation = gr.Markdown(
                    visible=False,
                )
                

def convert_history(chat_mdl: models.Chat):
    output = []
    for i in chat_mdl.messages:
        if i.sender == "user":
            output.append(
                (i.content, None)
            )
        else:
            output.append(
                (None, i.content)
            )

    return output

with gr.Blocks(title="AVERY") as avery_gradio:

    app = gr.mount_gradio_app(
        fastapi_app, 
        avery_gradio, 
        path="/write",
        favicon_path="/static/avery.ico",
    )

    generation_id_state = gr.State()
    generated_time_state = gr.State()
    generations_state = gr.State()
    round_id_state = gr.State()
    feedback_state = gr.State()
    
    ws_client = gr.State()

    async def initialize_interface(request: gr.Request):
        request = request.request
        leaderboard_id = request.session.get('leaderboard_id', None)
        program = request.session.get('program', None)
        play_round_ws = await Play_Round_WS.create(request=request, leaderboard_id=leaderboard_id, program=program)

        # Obtain original image
        response = await play_round_ws.start_resume(
            new_round=models.RoundStart(
                model="gpt-4o-mini",
                program=program,
                leaderboard_id=leaderboard_id,
                created_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
            ),
            resume=True
        )
        
        if response.round is None:
            round_id = None
        else:
            round_id = response.round.id
        original_img = play_round_ws.original_image

        # Set up the session
        generated_time = response.round.generated_time
        generation_id = response.generation.id if response.generation is not None else None
        generations = response.round.generations if response.round.generations is not None else []
        
        evaluation = gr.update(visible=False)
        interpreted_image = None
        interpreted_image_visible = gr.update(visible=False)
        detail_visible = gr.update()
        slider_update=gr.update()

        if response.round.generations:
            
            if 'AWE' in response.feedback:
                evaluation_msg = await obtain_evaluation_from_past(
                    generation_id=response.round.generations[-1],
                    request=request
                )
                if evaluation_msg:
                    evaluation = gr.update(value=evaluation_msg.replace("\n", "\n\n"), visible=True)

            if "IMG" in response.feedback:
                interpreted_image = await get_interpreted_image(
                    generation_id=response.round.generations[-1],
                    request=request
                )
                interpreted_image_visible = gr.update(visible=True)
            
            # Set slider
            total_generations = len(response.round.generations)
            slider_update = gr.update(maximum=total_generations, value=total_generations, interactive=True, visible=True)
            detail_visible = gr.update(visible=True,value=f"**あなたの回答**：\n\n{response.generation.sentence}")
        
        remain_time = MAX_GENERATION-len(generations)
        submit_btn_update = gr.update(interactive=False, value=f"送信(あと0回)")
        if remain_time>0:
            submit_btn_update = gr.update(interactive=True, value=f"送信(あと{remain_time}回)")
            
        chat_history = convert_history(response.chat)

        return original_img, play_round_ws, generated_time, chat_history, response.feedback, detail_visible, evaluation, interpreted_image, interpreted_image_visible, submit_btn_update, round_id, generations, slider_update
    
    async def ask_hint( message: str, chathist: list, ws: Play_Round_WS):
        if message == "":
            message = "ヒントをちょうだい。"
        chathist.append((message, None))
        new_message = models.MessageSend(
            content=message,
            created_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        )
        response = await ws.send_message(new_message)
        chat = response.chat
        new_msgs = convert_history(chat)
        chathist.extend(new_msgs)
        
        return None, chathist

    gr.Markdown(
    """
    各写真を注意深く観察し、写真に写っている人々、動物、または物について英語で150字以内で記述してください。回答は次の質問に焦点を当ててください：「写真には何が写っているのか」「それらは何をしているのか」「それらはどのように見えるのか（数や色など）」「それらはどこにいるのか」。写真に人が写っている場合は、その外見についても説明する必要があります。
    """
    )

    with gr.Row(equal_height=True,show_progress=True,elem_classes='top'):
        with gr.Column(min_width=200,elem_classes='bot'):
            guidance=Guidance()
            guidance.create_guidance()

            gr.on(triggers=[guidance.msg.submit,guidance.submit.click],
                  fn=ask_hint,
                  inputs=[guidance.msg, guidance.chat, ws_client],
                  outputs=[guidance.msg, guidance.chat],
            )

            # gr.Examples(
            #     examples=[
            #         ["この部屋の英語は何？"],
            #         ["この生物の色は何？"],
            #         ["関連動詞を提示してください"],
            #         ["The mouse is cutting a ham with a fork and knife."],
            #     ],
            #     inputs=[guidance.msg]
            # )

        with gr.Column(min_width=300,elem_classes='image'):
            writing = Writing()
            writing.create_original_image()

    with gr.Row(equal_height=True,show_progress=True,elem_classes='bottom'):
            writing.create_sentence()

            async def submit_answer(ws: Play_Round_WS, chat_history: list,sentence: str, generations: list, generated_time: int, generation_id: int, round_id: int):
                if sentence == "":
                    show = gr.update(visible=True)
                    Noshow = gr.update(visible=False)
                    return chat_history, show, generated_time, generation_id
                elif len(generations) >= MAX_GENERATION:
                    show = gr.update(visible=True)
                    Noshow = gr.update(visible=False)
                    return chat_history, show, generated_time, generation_id
                
                generated_time = generated_time + 1

                generation = models.GenerationStart(
                    round_id=round_id,
                    created_at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
                    generated_time=generated_time,
                    sentence=sentence,
                )
                response = await ws.send_answer(generation)
                
                if response.generation is not None: 
                    generation_id = response.generation.id
                    
                else:
                    generated_time = generated_time - 1
                    

                chat = response.chat
                if chat:
                    chat_history += convert_history(chat)
                return chat_history, generated_time, generation_id

            async def get_evaluation(ws: Play_Round_WS, feedback: str, chat_history: list,sentence: str, generated_time: int, generation_id: int, generations: list, request: gr.Request):

                if chat_history and chat_history[-1][1].startswith("ブー！"):
                    gr.Warning(chat_history[-1][1])

                if chat_history and chat_history[-1][1].startswith("ブー！") or len(generations) >= MAX_GENERATION or sentence == "":
                    ai_image_visible = gr.update()
                    ai_image=gr.update()
                    evaluation=gr.update()
                    answer_box=sentence
                    detail_visible = gr.update()
                    slider_update = gr.update()
                    submit_btn_update = gr.update()
                    return chat_history,ai_image_visible, ai_image, evaluation, answer_box, generated_time, generation_id, generations, detail_visible, slider_update, submit_btn_update
                request = request.request
                
                generated_time = generated_time + 1
                while True:
                    response = await ws.evaluate()
                    if not (response.feedback and response.feedback=="waiting"):
                        break
                
                chat = response.chat
                if chat:
                    chat_history += convert_history(chat)
                
                ai_image = None
                ai_image_visible = gr.update(visible=False)
                evaluation = gr.update(visible=False)
                slider_update = gr.update()

                if response.generation is not None: 
                    generation_id = response.generation.id
                    if generation_id not in generations:
                        generations.append(generation_id)
                    
                    detail_visible = gr.update(visible=True, value=f"**あなたの回答**：\n\n{sentence}")
                    total_generations=len(generations)
                    slider_update = gr.update(maximum=total_generations, value=total_generations, interactive=True, visible=True)

                    if "IMG" in feedback:
                        ai_image = await get_interpreted_image(
                            generation_id=generation_id,
                            request=request
                        )
                        ai_image_visible = gr.update(visible=True)


                    if "AWE" in feedback:
                        evaluation_msg = await obtain_evaluation_from_past(
                            generation_id=generation_id,
                            request=request
                        )
                        evaluation = gr.update(value=evaluation_msg.replace("\n", "\n\n"), visible=True)
                    
                    answer_box = ""
                else:
                    generated_time = generated_time - 1
                    detail_visible=gr.update()
                    answer_box = sentence
                remain_time = MAX_GENERATION-len(generations)
                submit_btn_update = gr.update(interactive=False, value=f"送信(あと0回)")
                if remain_time>0:
                    submit_btn_update = gr.update(interactive=True, value=f"送信(あと{remain_time}回)")
                return chat_history,ai_image_visible, ai_image, evaluation, answer_box, generated_time, generation_id, generations, detail_visible, slider_update, submit_btn_update

            writing.submit_btn.click(
                fn=submit_answer,
                inputs=[ws_client, guidance.chat, writing.sentence, generations_state, generated_time_state, generation_id_state, round_id_state],
                outputs=[guidance.chat, generated_time_state, generation_id_state],
            ).then(
                fn=get_evaluation,
                inputs=[ws_client, feedback_state, guidance.chat, writing.sentence, generated_time_state, generation_id_state, generations_state],
                outputs=[guidance.chat, writing.ai_image, writing.ai_image, writing.evaluation, writing.sentence, generated_time_state, generation_id_state, generations_state, writing.details, writing.slider, writing.submit_btn],
            )

            
            writing.sentence.submit(
                fn=submit_answer,
                inputs=[ws_client, guidance.chat, writing.sentence, generations_state, generated_time_state, generation_id_state, round_id_state],
                outputs=[guidance.chat, generated_time_state, generation_id_state],
            ).then(
                fn=get_evaluation,
                inputs=[ws_client, feedback_state, guidance.chat, writing.sentence, generated_time_state, generation_id_state, generations_state],
                outputs=[guidance.chat, writing.ai_image, writing.ai_image, writing.evaluation, writing.sentence, generated_time_state, generation_id_state, generations_state, writing.details, writing.slider, writing.submit_btn],
            )

            async def check_result_slider(slider_value: int, generations: list, feedback: str, request: gr.Request):
                request = request.request
                show_generation_id = generations[slider_value-1]

                gen = await get_generation(
                    generation_id=show_generation_id,
                    request=request
                )
                detail = gen.sentence

                if "IMG" in feedback:
                    ai_image = await get_interpreted_image(
                        generation_id=show_generation_id,
                        request=request
                    )
                else:
                    ai_image = None

                if "AWE" in feedback:
                    evaluation = await obtain_evaluation_from_past(
                        generation_id=show_generation_id,
                        request=request
                    )
                    evaluation = evaluation.replace("\n", "\n\n")
                else:
                    evaluation = None
                return detail, ai_image, evaluation

            writing.slider.release(
                fn=check_result_slider,
                inputs=[writing.slider, generations_state, feedback_state],
                outputs=[writing.details, writing.ai_image, writing.evaluation],
            )

            # gr.Examples(
            #     examples=[
            #         ["ネズミはハムをフォークとナイフで切っている。"],
            #         ["Shit"],
            #         ["The mouse is cutting a ham with a fork and knife."],
            #         ["A rabbit ran with a turtle confidently."]
            #     ],
            #     inputs=[sentence.sentence]
            # )

    avery_gradio.load(initialize_interface, inputs=[], outputs=[
        writing.image, 
        ws_client, 
        generated_time_state, 
        guidance.chat, 
        feedback_state, 
        writing.details,
        writing.evaluation, 
        writing.ai_image, 
        writing.ai_image, 
        writing.submit_btn, 
        round_id_state, 
        generations_state,
        writing.slider
    ])
    
    avery_gradio.queue(max_size=128, default_concurrency_limit=50)




