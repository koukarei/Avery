from ui import ui_gallery
from ui import ui_sentence
from ui import ui_result

from ui.ui_chatbot import Guidance
from ui.ui_result import Result

import gradio as gr
import os
import datetime
import time
import pandas as pd

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
        path="/dashboard", 
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY"),
    )


    gr.Markdown(
    """
    # ダッシュボード
    """
    )

    with gr.Column(show_progress=True,elem_classes='whole'):
        gr.Textbox(
            None,
            interactive=False,
        )
        # gr.LinePlot(df, x="weight", y="height")
        # gr.ScatterPlot(df, x="weight", y="height", color="ethnicity")


    avery_gradio.queue(max_size=128, default_concurrency_limit=50)




