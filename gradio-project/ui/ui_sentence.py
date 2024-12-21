import gradio as gr
from PIL import Image

from ui.ui_chatbot import Guidance

import os
import datetime

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from api.connection import get_original_images, create_generation, get_chat, send_message, get_interpretation, get_interpreted_image, read_my_rounds, get_generation
from api.connection import models

from app import app as fastapi_app


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

    def create_sentence(self):
        self.image=gr.Image(
            None,
            label="英作文を入力してください",
            interactive=False,
        )
        self.sentence=gr.Textbox(label='英作文',interactive=True, max_length=1000)

        self.submit_btn=gr.Button("送信",scale=0)

        self.ai_image=gr.Image(
            None,
            label="AIが生成した画像",
            interactive=False,
            visible=False,
        )

        self.next_btn=gr.Button("評価",scale=0,visible=False, link="/avery/go_to_result")
        

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

with gr.Blocks() as avery_gradio:

    app = gr.mount_gradio_app(
        fastapi_app, 
        avery_gradio, 
        path="/answer", 
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY"),
    )

    async def obtain_original_image(request: gr.Request):
        if not hasattr(app.state, 'selected_leaderboard'):
            return None, None
        
        original_img = await get_original_images(int(app.state.selected_leaderboard.id), request)
        generated_time = app.state.generated_time

        if generated_time:
            generations = app.state.round.generations
            if generations:
                generations = [i.id for i in generations]
                prev_generation_id = max(generations)
                prev_generation = await get_generation(prev_generation_id, request)
                prev_ans = prev_generation.sentence
            else:
                prev_ans = None
        else:
            prev_ans = None
        return original_img, prev_ans
    
    async def load_chat_content(request: gr.Request):
        if not hasattr(app.state, 'round'):
            raise Exception("Round not found")
        
        if app.state.round:
            chat = await get_chat(
                round_id=app.state.round.id,
                request=request,
            )
            if chat:
                yield convert_history(chat)
                return
            else:
                yield None

    async def ask_hint( message: str, request: gr.Request):
        if message == "":
            message = "ヒントをちょうだい。"
        round_id = app.state.round.id
        new_message = models.MessageSend(
            content=message,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        chat_mdl = await send_message(round_id, new_message, request)
        return None, convert_history(chat_mdl)

    gr.Markdown(
    """
    # この絵を英語で説明しましょう！
    """
    )

    with gr.Row(equal_height=True,show_progress=True,elem_classes='whole'):
        with gr.Column(min_width=200,elem_classes='bot'):
            guidance=Guidance()
            guidance.create_guidance()

            gr.on(triggers=[guidance.msg.submit,guidance.submit.click],
                  fn=ask_hint,
                  inputs=[guidance.msg],
                  outputs=[guidance.msg, guidance.chat],
                  queue=False
            )

            gr.Examples(
                examples=[
                    ["この部屋の英語は何？"],
                    ["この生物の色は何？"],
                    ["関連動詞を提示してください"],
                    ["The mouse is cutting a ham with a fork and knife."],
                ],
                inputs=[guidance.msg]
            )

        with gr.Column(min_width=300,elem_classes='interactive'):
            sentence=Sentence()
            sentence.create_sentence()

            async def submit_answer(chat_history: list,sentence: str, request: gr.Request):
                generated_time = int(app.state.generated_time) + 1

                generation = models.GenerationStart(
                    round_id=app.state.round.id,
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                    generated_time=generated_time,
                    sentence=sentence,
                )
                output = await create_generation(generation, request)
                if output:
                    app.state.generated_time = generated_time
                    app.state.generation = output
                    
                    show = gr.update(visible=True)
                    output = await get_interpretation(
                        round_id=app.state.round.id,
                        interpretation=output,
                        request=request,
                    )
                    
                    ai_image = await get_interpreted_image(
                        generation_id=output.id,
                        request=request
                    )
                else:
                    show = gr.update(visible=False)
                    ai_image = None

                chat = await get_chat(
                    round_id=app.state.round.id,
                    request=request,
                )
                if chat:
                    chat_history = convert_history(chat)
                return chat_history,show, show, ai_image

            gr.on(
                triggers=[sentence.submit_btn.click, sentence.sentence.submit],
                fn=submit_answer,
                inputs=[guidance.chat, sentence.sentence],
                outputs=[guidance.chat, sentence.ai_image, sentence.next_btn, sentence.ai_image],
                queue=False
            )

            gr.Examples(
                examples=[
                    ["ネズミはハムをフォークとナイフで切っている。"],
                    ["Shit"],
                    ["The mouse is cutting a ham with a fork and knife."],
                    ["A rabbit ran with a turtle confidently."]
                ],
                inputs=[sentence.sentence]
            )

    avery_gradio.load(obtain_original_image, inputs=[], outputs=[sentence.image, sentence.sentence])
    avery_gradio.load(load_chat_content, inputs=[], outputs=[guidance.chat])
    avery_gradio.queue(max_size=128, default_concurrency_limit=50)




