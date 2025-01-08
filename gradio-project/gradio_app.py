from ui.ui_result import app as fastapi_app

from ui.ui_chatbot import Guidance
from ui.ui_result import Result

import gradio as gr
import os
import datetime
import time
import pandas as pd

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from api.connection import read_leaderboard, get_users, get_original_images, get_chat, get_generations, get_interpreted_image
from api.connection import models

score_cat = [
    "n_words","n_conjunctions","n_adj","n_adv","n_pronouns","n_prepositions","n_grammar_errors","n_spelling_errors","perplexity","f_word","f_bigram","n_clauses","content_score"
]

color_map = {
    "n_words": "blue",
    "n_conjunctions": "red",
    "n_adj": "green",
    "n_adv": "purple",
    "n_pronouns": "orange",
    "n_prepositions": "yellow",
    "n_grammar_errors": "pink",
    "n_spelling_errors": "brown",
    "perplexity": "cyan",
    "f_word": "magenta",
    "f_bigram": "black",
    "n_clauses": "white",
    "content_score": "gray",
}

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
        path="/avery/dashboard/",
        root_path="/avery/dashboard"
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY"),
    )

    leaderboards = gr.State()
    selected_player = gr.State()
    selected_leaderboard = gr.State()
    selected_score = gr.State()
    generations = gr.State()
    users = gr.State()

    async def load_finished_game(request: gr.Request):
        leaderboards = await read_leaderboard(
            request=request,
        )
        print(leaderboards)
        leaderboard_choices = [i.title for i in leaderboards]
        generations = await get_generations(
            request=request,
        )
        print(generations)

        df_generations = pd.DataFrame([i.model_dump() for i,j in generations])

        value_vars = ["n_words","n_conjunctions","n_adj","n_adv","n_pronouns","n_prepositions","n_grammar_errors","n_spelling_errors","perplexity","f_word","f_bigram","n_clauses","content_score"]
        id_vars = df_generations.columns.difference(value_vars).tolist()

        df_generations = df_generations.melt(
            id_vars=id_vars,
            value_vars=value_vars,
            var_name="score_type",
            value_name="score",
        )

        role = app.state.session.get("roles")
        if role != "student":
            users = await get_users(request=request)
            user_choices = [i.profiles.display_name for i in users]
        else:
            users = None
            user_choices = None
        show = gr.update(visible=role != "student")
        return leaderboards, leaderboard_choices, generations, df_generations, users, user_choices, show

    with gr.Row():
        gr.Markdown(
        """
        # ダッシュボード
        """
        )

        gr.Button(
            "リーダーボード",
            scale=0,
            link="/avery/leaderboards",
        )

    with gr.Row():
        with gr.Column(show_progress=True,elem_classes='options', scale=1):
            user_choices = gr.Dropdown(
                choices = None,
                value = None,
                type = "index",
                multiselect = True,
                label = "ユーザー",
                visible = False,
                interactive = True,
            )

            leaderboard_choices = gr.Dropdown(
                choices = None,
                value = None,
                type = "index",
                label = "リーダーボード",
                multiselect = True,
                interactive = True,
            )

            score_choices = gr.Dropdown(
                ["字数", "接続詞", "形容詞", "副詞", "代名詞","前置詞","文法ミス数","スペルミス数","Perplexity","単語頻度","単語連続頻度","文節数","内容得点","全部"],
                value = ["全部"],
                multiselect = True,
                type = "index",
                label = "スコア",
                interactive = True,
                info="スコアの種類を選択してください。",
            )

        with gr.Column(show_progress=True,elem_classes='whole', scale=3):
            
            score_df = gr.ScatterPlot(
                None,
                x="duration",
                y="score",
                x_title="時間",
                y_title="スコア",
                title="スコア",
                color_map=color_map,
                color="score_type",
            )
            
            chat_history = gr.Chatbot(None)


    avery_gradio.load(load_finished_game, inputs=[],outputs=[leaderboards, leaderboard_choices, generations, score_df, users , user_choices, user_choices])
    avery_gradio.queue(max_size=128, default_concurrency_limit=50)




