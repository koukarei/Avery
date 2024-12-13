from ui import ui_gallery

from ui.ui_chatbot import Guidance
from ui.ui_sentence import Sentence

import gradio as gr
import os
import datetime

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from api.connection import get_original_images, create_generation
from api.connection import models

from app import app as fastapi_app


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
        return await get_original_images(int(app.state.selected_leaderboard.id), request)

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
                  fn=guidance.slow_echo,
                  inputs=[guidance.msg,guidance.chat,game_data],
                  outputs=[guidance.msg,guidance.chat,game_data])

        with gr.Column(min_width=300,elem_classes='interactive'):
            sentence=Sentence()
            sentence.create_sentence()

            async def submit_answer(sentence: str, request: gr.Request):
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
                    return output

            gr.on(triggers=[sentence.submit_btn.click, sentence.sentence.submit],
                  fn=submit_answer,
                  inputs=[sentence.sentence],
                  outputs=None)


    avery_gradio.load(obtain_original_image, inputs=[], outputs=[sentence.image])
    avery_gradio.queue(max_size=128, default_concurrency_limit=50)




