import gradio as gr
import os
from typing import Optional
import requests
import datetime

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, Response
from api.connection import read_leaderboard, get_original_images, get_interpreted_image, get_rounds, get_generation, check_playable, read_my_rounds
from api.connection import models

from app import app as fastapi_app

class Gallery:
    """Create a gallery object for the user interface."""

    def __init__(self, text_file_path="data/text_files"):
        self.text_file_path = text_file_path
        self.gallery = None
        self.image = None
        self.submit_btn = None
        self.selected=None
        self.ai_img=None
        self.transform_img=None
    
    def create_gallery(self):
        with gr.Column(elem_classes="gallery"):
            with gr.Row():
                with gr.Column():
                    self.gallery = gr.Gallery(None, label="Original", interactive=False)
                with gr.Column():
                    self.info = gr.Markdown(None)
                    self.generated_img = gr.Gallery(None, label="record")
            with gr.Row():
                self.submit_btn = gr.Button("始める", scale=0, interactive=False, link="/go_to_answer")

    def upload_picture(self, image):
        return image[0][0]
    
    def on_select(self, evt: gr.SelectData):
        self.selected=evt.value['image']['path']
        return evt.value['image']['path']


with gr.Blocks() as avery_gradio:
    
    gallery=Gallery()

    unfinished = gr.State()
    
    async def initialize_game(request: gr.Request):
        leaderboards = await read_leaderboard(request)
        return [
            await get_original_images(leaderboard.id, request) 
            for leaderboard in leaderboards
        ], leaderboards
    
    async def get_unfinished_rounds_from_backend(request: gr.Request, leaderboard_id: int):
        rounds = await read_my_rounds(
            request=request,
            is_completed=False,
            leaderboard_id=leaderboard_id,
        )
        
        return rounds

    with gr.Row():
        gr.Markdown(
        """
        # AVERYにようこそ！
        このゲームは、Averyと一緒に画像を解釈するゲームです。

        まずは、ギャラリーから画像を選択してください。
        """
        )

        gr.Button(
            "ダッシュボード",
            scale=0,
            link="/dashboard",
        )

    leaderboards = gr.State()
    selected_leaderboard = gr.State()
    related_generations = gr.State()

    gallery.create_gallery()

    try: 
        avery_gradio.load(initialize_game, inputs=[], outputs=[gallery.gallery,leaderboards])
    except Exception as e:
        RedirectResponse(url="/")

    avery_gradio.queue(max_size=128, default_concurrency_limit=50)

    app = gr.mount_gradio_app(
        fastapi_app, 
        avery_gradio, 
        path="/leaderboards", 
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY"),
    )

    async def select_leaderboard(evt: gr.SelectData, leaderboards, request: gr.Request):
        select_leaderboard = leaderboards[evt.index]

        app.state.selected_leaderboard = select_leaderboard
        info = f"## {select_leaderboard.title}"
        rounds = await get_rounds(select_leaderboard.id, request=request)
        if rounds:
            generations = [generation for round in rounds for generation in round.generations]
            interpreted_images = []
            not_working = []
            for generation in generations:
                interpreted_img = await get_interpreted_image(generation_id=generation.id, request=request)
                if interpreted_img:
                    interpreted_images.append(interpreted_img)
                else:
                    not_working.append(generation)
            if not_working:
                generations = [generation for generation in generations if generation not in not_working]
        else:
            interpreted_images = None
            generations = None
        
        # Check if the player played the game before
        playable = await check_playable(select_leaderboard.id, request=request)
        start_btn = gr.update(value="始める",interactive=playable, link="/go_to_answer")
        unfinished_rounds = None
        if not playable:
            unfinished_rounds = await get_unfinished_rounds_from_backend(request, select_leaderboard.id)
            if unfinished_rounds:
                start_btn = gr.update(value="再開", link="/resume_game",interactive=True)
            
        return select_leaderboard, start_btn, info, interpreted_images, generations, unfinished_rounds

    async def select_interpreted_image(evt: gr.SelectData, generations, select_leaderboard, request: gr.Request):
        selected_interpreted = generations[evt.index]
        selected = await get_generation(selected_interpreted.id, request)
        if selected:
            md = f"""## {select_leaderboard.title}
            
            英作文：{selected.sentence}

            合計点：{selected.total_score}
            
            ランク：{selected.rank}"""
        else:
            md = f"## {select_leaderboard.title}"
        return md
            

    # Set the selected leaderboard
    gr.on(
        triggers=[gallery.gallery.select],
        fn=select_leaderboard,
        inputs=[leaderboards],
        outputs=[selected_leaderboard, gallery.submit_btn, gallery.info, gallery.generated_img, related_generations, unfinished],
    )

    # Set the selected interpreted image
    gr.on(
        triggers=[gallery.generated_img.select],
        fn=select_interpreted_image,
        inputs=[related_generations, selected_leaderboard],
        outputs=[gallery.info],
    )




