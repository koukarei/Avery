import gradio as gr
import os
from typing import Optional
import requests
import datetime

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, Response
from api.connection import read_leaderboard, get_original_images, get_interpreted_image, get_rounds, get_generation, check_playable, read_my_rounds, get_generations, delete_leaderboard
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
                    self.info = gr.Markdown(None, line_breaks=True)
                    self.generated_img = gr.Gallery(None, label="record")
            with gr.Row():
                self.submit_btn = gr.Button("始める", scale=0, interactive=False, link="/avery/go_to_answer")
                self.delete_btn = gr.Button("削除", scale=0, visible=False)

    def upload_picture(self, image):
        return image[0][0]
    
    def on_select(self, evt: gr.SelectData):
        self.selected=evt.value['image']['path']
        return evt.value['image']['path']


with gr.Blocks() as avery_gradio:
    
    gallery=Gallery()

    unfinished = gr.State()
    
    async def initialize_game(request: gr.Request, published_at_start: Optional[datetime.datetime]=None, published_at_end: Optional[datetime.datetime]=None):
        if published_at_start and published_at_end:
            published_at_start = datetime.datetime.fromtimestamp(published_at_start)
            published_at_end = datetime.datetime.fromtimestamp(published_at_end)
            
            leaderboards = await read_leaderboard(request, published_at_start, published_at_end)
        elif published_at_start:
            published_at_start = datetime.datetime.fromtimestamp(published_at_start)
            leaderboards = await read_leaderboard(request, published_at_start)
        elif published_at_end:
            published_at_end = datetime.datetime.fromtimestamp(published_at_end)
            leaderboards = await read_leaderboard(request, published_at_end=published_at_end)
        else:
            published_at_start = datetime.datetime.now()
            published_at_end = datetime.datetime.now()
            leaderboards = await read_leaderboard(request, published_at_start, published_at_end)
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
        with gr.Column():
            gr.Markdown(
            """
            # AVERYにようこそ！
            このゲームは、Averyと一緒に画像を解釈するゲームです。

            まずは、ギャラリーから画像を選択してください。
            """
            )

        with gr.Column():
            with gr.Row():
                gr.Button(
                    "ダッシュボード",
                    scale=0,
                    link="/avery/dashboard",
                )

                gr.Button(
                    "ログアウト",
                    scale=0,
                    link="/avery/logout",
                )
            with gr.Row():
                published_at_start_dropdown = gr.DateTime(include_time=False, label="公開日")
                published_at_end_dropdown = gr.DateTime(include_time=False, label="〜")

    leaderboards = gr.State()
    selected_leaderboard = gr.State()
    related_generations = gr.State()

    gallery.create_gallery()

    try: 
        avery_gradio.load(initialize_game, inputs=[published_at_start_dropdown, published_at_end_dropdown], outputs=[gallery.gallery,leaderboards])
    except Exception as e:
        RedirectResponse(url="/avery/")

    avery_gradio.queue(max_size=128, default_concurrency_limit=50)

    app = gr.mount_gradio_app(
        fastapi_app, 
        avery_gradio, 
        path="/",
        root_path="/avery/leaderboards",
    )
    print(f"Gradio root path: {avery_gradio.root_path}")
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY"),
    )

    async def select_leaderboard_fn(evt: gr.SelectData, leaderboards, request: gr.Request):
        select_leaderboard = leaderboards[evt.index]

        app.state.selected_leaderboard = select_leaderboard

        # Get the related vocabularies
        leaderboard_vocabularies = [v.word for v in select_leaderboard.vocabularies]
        leaderboard_vocabularies = "/ ".join(leaderboard_vocabularies)
        if leaderboard_vocabularies:
            leaderboard_vocabularies=f"\n\n関連単語：*{leaderboard_vocabularies}*"
        else:
            leaderboard_vocabularies=""
        
        info = f"## {select_leaderboard.title}{leaderboard_vocabularies}"
        if hasattr(app, "school"):
            school_name = app.state.get("school")
        else:
            school_name = None
        round_generations = await get_generations(leaderboard_id=select_leaderboard.id,school_name=school_name, request=request)
        if round_generations:
            interpreted_images = []
            not_working = []
            for round_generation in round_generations:
                interpreted_img = await get_interpreted_image(generation_id=round_generation.generation.id, request=request)
                if interpreted_img:
                    interpreted_images.append(interpreted_img)
                else:
                    not_working.append(round_generation)
            if not_working:
                round_generations = [generation for generation in round_generations if generation not in not_working]
        else:
            interpreted_images = None
            round_generations = None
        
        # Check if the player played the game before
        playable = await check_playable(select_leaderboard.id, request=request)
        start_btn = gr.update(value="始める",interactive=playable, link="/avery/go_to_answer")

        # Check if the player is an admin
        delete_btn = gr.update(visible=False)
        if hasattr(request.session, "roles") and request.session.get("roles") != "student":
            if hasattr(request.session, "username") and request.session.get("username") == "admin":
                delete_btn = gr.update(visible=True)
                
        unfinished_rounds = await get_unfinished_rounds_from_backend(request, select_leaderboard.id)
        if unfinished_rounds:
            start_btn = gr.update(value="再開", link="/avery/resume_game",interactive=True)
            
        return select_leaderboard, start_btn, delete_btn, info, interpreted_images, round_generations, unfinished_rounds

    async def delete_selected_leaderboard(request: gr.Request, selected_leaderboard, published_at_start: Optional[datetime.datetime]=None, published_at_end: Optional[datetime.datetime]=None):
        leaderboard = await delete_leaderboard(selected_leaderboard.id, request=request)
        leaderboards = await read_leaderboard(request, published_at_start, published_at_end)
        return [
            await get_original_images(leaderboard.id, request) 
            for leaderboard in leaderboards
        ], leaderboards

    async def select_interpreted_image(evt: gr.SelectData, generations, select_leaderboard, request: gr.Request):
        selected_interpreted = generations[evt.index]
        selected_round = selected_interpreted.round
        selected = selected_interpreted.generation

        leaderboard_vocabularies=[v.word for v in select_leaderboard.vocabularies]
        leaderboard_vocabularies="/ ".join(leaderboard_vocabularies)
        if leaderboard_vocabularies:
            leaderboard_vocabularies=f"\n\n関連単語：*{leaderboard_vocabularies}*"
        else:
            leaderboard_vocabularies=""

        if selected:
            if hasattr(selected, 'score'):
                score = selected.score
                duration = round(selected.duration/60,2)
                
                if hasattr(request.session, "roles") and request.session.get("roles")!= "student":
                    player_name = "作成者：{}　".format(selected_round.player.display_name)
                else:
                    player_name = ""

                md = f"""## {select_leaderboard.title}{leaderboard_vocabularies}

---

英作文：{selected.correct_sentence}

{player_name}作成時間：{selected_round.created_at}

文法得点：{score.grammar_score}　スペル得点：{score.spelling_score}

鮮明さ：{score.vividness_score}　自然さ：{int(score.convention)}　構造性：{score.structure_score}

内容得点：{score.content_score}　合計点：{selected.total_score}

ランク：{selected.rank}　時間：{duration}秒　類似度： {round(score.image_similarity*100, 2)}%"""
            else:
                md = f"""## {select_leaderboard.title}{leaderboard_vocabularies}

---

英作文：{selected.correct_sentence}"""
        else:
            md = f"## {select_leaderboard.title}{leaderboard_vocabularies}"
        return md
            

    # Load leaderboards
    gr.on(
        triggers=[published_at_start_dropdown.change, published_at_end_dropdown.change],
        fn=initialize_game,
        inputs=[published_at_start_dropdown, published_at_end_dropdown],
        outputs=[gallery.gallery, leaderboards],
    )

    # Set the selected leaderboard
    gr.on(
        triggers=[gallery.gallery.select],
        fn=select_leaderboard_fn,
        inputs=[leaderboards],
        outputs=[selected_leaderboard, gallery.submit_btn, gallery.delete_btn, gallery.info, gallery.generated_img, related_generations, unfinished],
    )

    # Set the selected interpreted image
    gr.on(
        triggers=[gallery.generated_img.select],
        fn=select_interpreted_image,
        inputs=[related_generations, selected_leaderboard],
        outputs=[gallery.info],
    )

    # Delete the selected leaderboard
    gr.on(
        triggers=[gallery.delete_btn.click],
        fn=delete_selected_leaderboard,
        inputs=[selected_leaderboard, published_at_start_dropdown, published_at_end_dropdown],
        outputs=[gallery.gallery, leaderboards],
    )




