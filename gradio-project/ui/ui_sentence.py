import gradio as gr
from PIL import Image

from ui.ui_chatbot import Guidance

import os
import datetime

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from api.connection import get_original_images, create_generation, get_chat, send_message, get_interpretation, get_interpreted_image, read_my_rounds, get_generation
from api.connection import models

from ui.ui_gallery import app as fastapi_app


class Sentence:
    """Combine keywords into a sentence.
        Let AI to check the sentence.
    """

    def __init__(self):
        self.sentence=None
        self.submit_btn=None
        self.image=None
        self.ai_image=None
        self.next_btn=None

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
                self.ai_image=gr.Image(
                    None,
                    label="AIが生成した画像",
                    interactive=False,
                    visible=False,
                )

            with gr.Row():
                self.next_btn=gr.Button("評価",scale=0,visible=False, link="")
        

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
        path="/answer",
        favicon_path="/static/favicon.ico",
    )

    generation_id = gr.State()
    generated_time = gr.State()

    async def obtain_original_image(request: gr.Request):
        request = request.request
        leaderboard_id = request.session.get('leaderboard_id', None)

        original_img = await get_original_images(int(leaderboard_id), request)
        generated_time = request.session.get('generated_time', 0)
        current_round = request.session.get('round', None)

        if not current_round:
            current_round = await read_my_rounds(
                    request=request,
                    is_completed=False,
                    leaderboard_id=leaderboard_id,
                )

            latest_round = max(current_round, key=lambda x: x.created_at)
            generations = latest_round.generations
            
            if generations:
                generations = [i.id for i in generations]
                prev_generation_id = max(generations)
                prev_generation = await get_generation(prev_generation_id, request)
                prev_ans = prev_generation.sentence
            else:
                prev_ans = None
                
        elif 'generations' in current_round:
            generations = current_round['generations']
            prev_ans = None
            if generations:
                generations = [i['id'] for i in generations]
                prev_generation_id = max(generations)
                prev_generation = await get_generation(prev_generation_id, request)
                prev_ans = prev_generation.sentence
        else:
            prev_ans = None
            
        return original_img, prev_ans, generated_time
    
    async def load_chat_content(request: gr.Request):
        request = request.request
        cur_round = request.session.get('round', None)
        if not cur_round:
            raise Exception("Round not found")
        else: 
            chat = await get_chat(
                round_id=cur_round["id"],
                request=request,
            )
            if chat:
                yield convert_history(chat)
                return
            else:
                yield None

    async def ask_hint( message: str, chathist , request: gr.Request):
        request = request.request
        cur_round = request.session.get('round', None)
        if not cur_round:
            raise Exception("Round not found")
        if message == "":
            message = "ヒントをちょうだい。"
        round_id = cur_round['id']
        new_message = models.MessageSend(
            content=message,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        chat_mdl = await send_message(round_id, new_message, request)
        new_msg = convert_history(chat_mdl)
        len_new_msg = len(new_msg)-len(chathist)

        for i in range(len_new_msg):
            chathist.append(new_msg[-len_new_msg+i])
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
                  inputs=[guidance.msg, guidance.chat],
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
            sentence=Sentence()
            sentence.create_original_image()

    with gr.Row(equal_height=True,show_progress=True,elem_classes='bottom'):
            sentence.create_sentence()

            async def submit_answer(chat_history: list,sentence: str, generated_time: int, generation_id: int, request: gr.Request):
                if sentence == "":
                    show = gr.update(visible=True)
                    Noshow = gr.update(visible=False)
                    return chat_history, None, Noshow, Noshow, show, show, generated_time, generation_id
                
                request = request.request
                generated_time = generated_time + 1

                cur_round = request.session.get('round', None)

                generation = models.GenerationStart(
                    round_id=cur_round['id'],
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                    generated_time=generated_time,
                    sentence=sentence,
                )
                output = await create_generation(generation, request)
                
                if output:
                    generation_id = output.id
                    show = gr.update(visible=True)
                    
                    await get_interpretation(
                        round_id=cur_round['id'],
                        interpretation=output,
                        request=request,
                    )
                    
                    ai_image = await get_interpreted_image(
                        generation_id=generation_id,
                        request=request
                    )
                    submit_show = gr.update(visible=False)
                    sentence_interactive = gr.update(interactive=False)
                    link = "/avery/go_to_result/{}".format(generation_id)
                    next_btn = gr.update(link=link, visible=True)
                else:
                    generated_time = generated_time - 1
                    show = gr.update(visible=False)
                    ai_image = None
                    submit_show = gr.update(visible=True)
                    sentence_interactive = gr.update(interactive=True)
                    next_btn = gr.update(visible=False)

                chat = await get_chat(
                    round_id=cur_round['id'],
                    request=request,
                )
                if chat:
                    chat_history = convert_history(chat)
                return chat_history,show, next_btn, ai_image, submit_show, sentence_interactive, generated_time, generation_id

            gr.on(
                triggers=[sentence.submit_btn.click, sentence.sentence.submit],
                fn=submit_answer,
                inputs=[guidance.chat, sentence.sentence, generated_time, generation_id],
                outputs=[guidance.chat, sentence.ai_image, sentence.next_btn, sentence.ai_image, sentence.submit_btn,sentence.sentence, generated_time, generation_id],
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

    avery_gradio.load(obtain_original_image, inputs=[], outputs=[sentence.image, sentence.sentence, generated_time])
    avery_gradio.load(load_chat_content, inputs=[], outputs=[guidance.chat])
    avery_gradio.queue(max_size=128, default_concurrency_limit=50)




