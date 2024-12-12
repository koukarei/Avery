import gradio as gr
import os
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from api.connection import *

from app import app as fastapi_app

#from ui.ui_init import Guidance
from ui.ui_gallery import Gallery
# from ui.ui_sentence import Sentence
# from ui.ui_interpreted_image import InterpretedImage
# from ui.ui_result import Result

with gr.Blocks() as avery_gradio:
    
    step_list_start= [
        {"name":"Select/Upload Image","Interactive":True},
        {"name":"Sentence","Interactive":False},
        {"name":"Verify","Interactive":False},
        {"name":"Results","Interactive":False},
    ]

    async def initialize_game(request: gr.Request):
        leaderboards = await read_leaderboard(request)
        return [
            await get_original_images(leaderboard.id, request) 
            for leaderboard in leaderboards
        ]
    
    gallery=Gallery()
    # sentence=Sentence()
    # interpreted_image=InterpretedImage()
    # result=Result()

    gallery.create_gallery()

    avery_gradio.load(initialize_game, inputs=[
    ], outputs=gallery.gallery)
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