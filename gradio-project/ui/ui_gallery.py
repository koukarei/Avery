import gradio as gr
import os
from typing import Optional
import requests
import datetime

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, Response
from api.connection import read_leaderboard, get_original_images, get_interpreted_image, get_rounds, get_generation, check_playable, read_my_rounds, get_generations, delete_leaderboard, update_leaderboard, get_schools
from api.connection import models

from app import app as fastapi_app
from app import get_root_url
import gradio.route_utils 
gradio.route_utils.get_root_url = get_root_url

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
                self.published_at = gr.DateTime(include_time=False, label="公開日", visible=False)
                self.is_public = gr.Checkbox("is_public", label="公開", visible=False)
                self.school_group = gr.CheckboxGroup(["saikyo", "lms"], label="学校", info="Which school can access this leaderboard?", visible=False)
                self.word = gr.Textbox(label="word", placeholder="word", visible=False)
                self.pos = gr.Textbox(label="pos", placeholder="pos", visible=False)
                self.meaning = gr.Textbox(label="meaning", placeholder="meaning", visible=False)
                self.update_btn = gr.Button("更新", scale=0, visible=False)

    def upload_picture(self, image):
        return image[0][0]
    
    def on_select(self, evt: gr.SelectData):
        self.selected=evt.value['image']['path']
        return evt.value['image']['path']


with gr.Blocks() as avery_gradio:
    
    gallery=Gallery()

    unfinished = gr.State()
    
    async def initialize_game(request: gr.Request, published_at_start: Optional[datetime.datetime]=None, published_at_end: Optional[datetime.datetime]=None):
        is_admin = False
        request = request.request
        if hasattr(request, "session"):
            if isinstance(request.session, dict) and request.session.get("roles") != "student" and request.session.get("username") == "admin":
                is_admin = True
        
        if published_at_start and published_at_end:
            published_at_start = datetime.datetime.fromtimestamp(published_at_start)
            published_at_end = datetime.datetime.fromtimestamp(published_at_end)
            
            leaderboards = await read_leaderboard(request, published_at_start, published_at_end, is_admin=is_admin)
        elif published_at_start:
            published_at_start = datetime.datetime.fromtimestamp(published_at_start)
            leaderboards = await read_leaderboard(request, published_at_start, is_admin=is_admin)
        elif published_at_end:
            published_at_end = datetime.datetime.fromtimestamp(published_at_end)
            leaderboards = await read_leaderboard(request, published_at_end=published_at_end, is_admin=is_admin)
        else:
            #published_at_start = datetime.datetime.now()
            published_at_start = datetime.datetime(2025,1,9)
            published_at_end = datetime.datetime.now()
            leaderboards = await read_leaderboard(request, published_at_start, published_at_end, is_admin=is_admin)
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
                    visible=False,
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
        path="/leaderboards",
    )

    async def select_leaderboard_fn(evt: gr.SelectData, leaderboards, request: gr.Request):
        request = request.request
        select_leaderboard = leaderboards[evt.index]
        
        # Get the related vocabularies
        leaderboard_vocabularies = [v.word for v in select_leaderboard.vocabularies]
        leaderboard_vocabularies = "/ ".join(leaderboard_vocabularies)
        if leaderboard_vocabularies:
            leaderboard_vocabularies=f"\n\n関連単語：*{leaderboard_vocabularies}*"
        else:
            leaderboard_vocabularies=""
        
        info = f"## {select_leaderboard.title}{leaderboard_vocabularies}"
        if hasattr(request,"session") and isinstance(request.session, dict): 
            school_name = request.session.get("school", None)
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
        start_btn = gr.update(value="始める",interactive=playable, link="/avery/go_to_answer/{}".format(select_leaderboard.id))

        # Check if the player is an admin
        is_admin = gr.update(visible=False)
        schools = []

        if hasattr(request, "session"):
            if isinstance(request.session, dict) and request.session.get("roles", None) != "student" and request.session.get("username", None) == "admin":
                is_admin = gr.update(visible=True)
                schools = await get_schools(request=request, leaderboard_id=select_leaderboard.id)

        unfinished_rounds = await get_unfinished_rounds_from_backend(request, select_leaderboard.id)
        if unfinished_rounds:
            link = "/avery/resume_game/{}".format(select_leaderboard.id)
            start_btn = gr.update(value="再開", link=link,interactive=True)
            
        
        return select_leaderboard, start_btn, is_admin, info, interpreted_images, round_generations, unfinished_rounds,is_admin,is_admin,is_admin,is_admin,is_admin,is_admin, is_admin, select_leaderboard.is_public, select_leaderboard.published_at, schools

    async def delete_selected_leaderboard(request: gr.Request, selected_leaderboard, published_at_start: Optional[datetime.datetime]=None, published_at_end: Optional[datetime.datetime]=None):
        request = request.request
        leaderboard = await delete_leaderboard(selected_leaderboard.id, request=request)
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

    async def select_interpreted_image(evt: gr.SelectData, generations, select_leaderboard, request: gr.Request):
        request = request.request
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
                
                if hasattr(request, 'session') and isinstance(request.session, dict) and request.session.get("roles", None) != "student":
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

    async def submit_update_leaderboard(selected_leaderboard, is_public, published_at, schools, word, pos, meaning, request: gr.Request):
        request = request.request
        leaderboard_id = selected_leaderboard.id
        
        published_at = datetime.datetime.fromtimestamp(published_at)
        if not all([word, pos, meaning]):
            vocabularies = []
        else:
            vocabularies = [models.VocabularyBase(word=word, pos=pos, meaning=meaning)]
        leaderboard = models.LeaderboardUpdate(
            id = leaderboard_id,
            is_public=is_public,
            published_at=published_at,
            school=schools,
            vocabularies=vocabularies,
        )
        leaderboard = await update_leaderboard(leaderboard, request=request)
        schools = await get_schools(request=request, leaderboard_id=leaderboard_id)
        leaderboard_published_at = leaderboard.published_at.timestamp()
        return leaderboard.is_public, leaderboard_published_at, schools, '', '', ''

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
        outputs=[
            selected_leaderboard, 
            gallery.submit_btn, 
            gallery.delete_btn, 
            gallery.info, 
            gallery.generated_img, 
            related_generations, 
            unfinished, 
            gallery.is_public,
            gallery.published_at,
            gallery.school_group,
            gallery.word,
            gallery.pos,
            gallery.meaning,
            gallery.update_btn,
            gallery.is_public,
            gallery.published_at,
            gallery.school_group,
        ],
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

    # Change accessibilities of the schools
    gr.on(
        triggers=[gallery.update_btn.click],
        fn=submit_update_leaderboard,
        inputs=[selected_leaderboard, gallery.is_public, gallery.published_at, gallery.school_group, gallery.word, gallery.pos, gallery.meaning],
        outputs=[gallery.is_public, gallery.published_at, gallery.school_group, gallery.word, gallery.pos, gallery.meaning],
    )




