import gradio as gr
import os
import requests
import datetime

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, Response
from api.connection import read_leaderboard, get_original_images, create_round
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
            self.gallery = gr.Gallery(None, label="Original", interactive=False)
            with gr.Row():
                self.submit_btn = gr.Button("送信", scale=0, interactive=False)
                self.next_btn = gr.Button("次へ", scale=0, visible=False, link="/")

    def upload_picture(self, image):
        return image[0][0]
    
    def on_select(self, evt: gr.SelectData):
        self.selected=evt.value['image']['path']
        return evt.value['image']['path']


with gr.Blocks() as avery_gradio:
    
    gallery=Gallery()
    
    async def initialize_game(request: gr.Request):
        leaderboards = await read_leaderboard(request)
        return [
            await get_original_images(leaderboard.id, request) 
            for leaderboard in leaderboards
        ], leaderboards

    gr.Markdown(
    """
    # AVERYにようこそ！
    このゲームは、Averyと一緒に画像を解釈するゲームです。

    まずは、ギャラリーから画像を選択してください。
    """
    )

    leaderboards = gr.State()
    selected_leaderboard = gr.State()
    new_round = gr.State()

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

    def select_leaderboard(evt: gr.SelectData, leaderboards):
        select_leaderboard = leaderboards[evt.index]
        round_start = models.RoundStart(
            leaderboard_id=select_leaderboard.id,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        app.state.selected_leaderboard = select_leaderboard
        
        return select_leaderboard, gr.update(interactive=True), round_start

    # Set the selected leaderboard
    gr.on(
        triggers=[gallery.gallery.select],
        fn=select_leaderboard,
        inputs=[leaderboards],
        outputs=[selected_leaderboard, gallery.submit_btn, new_round],
    )

    async def create_new_round(new_round: models.RoundStart, request: gr.Request):
        output = await create_round(
            new_round=new_round,
            request=request,
        )
        
        app.state.round = output
        app.state.generated_time = 0
        return output, gr.update(visible=True)

    # Create a new round
    gr.on(
        triggers=[gallery.submit_btn.click],
        fn=create_new_round,
        inputs=[new_round],
        outputs=[new_round, gallery.next_btn],
    )

