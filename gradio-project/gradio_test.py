from ui import ui_gallery
from ui import ui_sentence

from ui.ui_chatbot import Guidance
from ui.ui_result import Result

import gradio as gr
import os
import datetime
import time

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from api.connection import get_original_images, get_image_similarity, get_chat, send_message, get_interpreted_image, complete_generation, end_round
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
        path="/result", 
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY"),
    )

    async def obtain_image(request: gr.Request):
        if not hasattr(app.state, 'selected_leaderboard'):
            return None
        elif not hasattr(app.state, 'generation'):
            return None
        
        original_img = await get_original_images(int(app.state.selected_leaderboard.id), request)
        ai_img = await get_interpreted_image(int(app.state.generation.id), request)
        similarity = await get_image_similarity(int(app.state.generation.id), request)
        print(similarity)
        if similarity:
            similarity = float(similarity["blip2_score"])*100
        similarity_md = "# 類似度: {:^10.2f} ".format(similarity)
        return original_img, ai_img, similarity_md
    
    async def load_chat_content(request: gr.Request):
        # complete the generation and get the chat
        if not hasattr(app.state, 'generation'):
            raise Exception("Generation not found")
        
        if not hasattr(app.state, 'round'):
            raise Exception("Round not found")

        if app.state.round:
            chat = await get_chat(
                round_id=app.state.round.id,
                request=request,
            )

            if chat:
                check_generated_time = app.state.generated_time < 3
                show_restart = gr.update(visible=check_generated_time)
                show_end = gr.update(visible=True)
                yield convert_history(chat), show_restart, show_end
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
    # 評価
    """
    )

    with gr.Column(show_progress=True,elem_classes='whole'):

        guidance=Guidance()
        guidance.create_guidance()

        gr.on(triggers=[guidance.msg.submit,guidance.submit.click],
                fn=ask_hint,
                inputs=[guidance.msg, guidance.chat],
                outputs=[guidance.msg, guidance.chat],
                queue=False
        )

        result=Result()
        result.create_result()


    avery_gradio.load(obtain_image, inputs=[], outputs=[result.image, result.ai_image, result.similarity])
    avery_gradio.load(load_chat_content, inputs=[], outputs=[guidance.chat, result.restart_btn, result.end_btn])
    avery_gradio.queue(max_size=128, default_concurrency_limit=50)




