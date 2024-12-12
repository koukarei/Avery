import gradio as gr
import os
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from api.connection import *

from app import app as fastapi_app

with gr.Blocks() as avery_gradio:
    
    async def record_initial_startup(request: gr.Request):
        await read_leaderboard(request)
    avery_gradio.load(record_initial_startup, inputs=[

    ], outputs=None)
    avery_gradio.queue(max_size=128, default_concurrency_limit=50)

    app = gr.mount_gradio_app(
        fastapi_app, 
        avery_gradio, 
        path="/game", 
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY"),
    )