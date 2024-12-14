from ui import ui_gallery

from ui.ui_chatbot import Guidance
from ui.ui_sentence import Sentence

import gradio as gr
import os
import datetime
import time

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from api.connection import get_original_images, create_generation, get_chat, send_message
from api.connection import models

from app import app as fastapi_app


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
            return None
        return await get_original_images(int(app.state.selected_leaderboard.id), request)
    
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

    async def ask_hint( message: str, chat_history: list, request: gr.Request):
        if message == "":
            return None, chat_history
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
                  inputs=[guidance.msg, guidance.chat],
                  outputs=[guidance.msg, guidance.chat]
            )

        with gr.Column(min_width=300,elem_classes='interactive'):
            sentence=Sentence()
            sentence.create_sentence()

            async def submit_answer(sentence: str, request: gr.Request):
                generated_time = int(app.state.generated_time) + 1

                generation = models.GenerationStart(
                    round_id=request.app.state.round.id,
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                    generated_time=generated_time,
                    sentence=sentence,
                )
                output = await create_generation(generation, request)
                if output:
                    app.state.generated_time = generated_time
                    app.state.generation = output
                    return output

            gr.on(triggers=[sentence.submit_btn.click, sentence.sentence.submit],
                  fn=submit_answer,
                  inputs=[sentence.sentence],
                  outputs=None)


    avery_gradio.load(obtain_original_image, inputs=[], outputs=[sentence.image])
    avery_gradio.load(load_chat_content, inputs=[], outputs=[guidance.chat])
    avery_gradio.queue(max_size=128, default_concurrency_limit=50)




