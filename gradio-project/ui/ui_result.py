import gradio as gr

from ui.ui_chatbot import Guidance

import os
import datetime

from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from api.connection import get_original_images, get_image_similarity, get_chat, send_message, get_interpreted_image
from api.connection import models

from ui.ui_sentence import app as fastapi_app

MAX_GENERATION = int(os.getenv("MAX_GENERATION", 5))

import gradio as gr

class Result:
    def __init__(self):
        self.image=None
        self.similarity=None
        self.ai_image=None
        self.restart_btn=None
        self.end_btn=None
        self.checkbox=None


    def create_result(self):
        with gr.Row():
            self.similarity=gr.Markdown("Similarity")

        with gr.Row():
            self.image=gr.Image(None,label="Original",interactive=False)
            self.ai_image=gr.Image(None,label="Interpreted",interactive=False)
        
        with gr.Row():
            self.confirm_txt=gr.Markdown("この画像を一度終了すると、再度再生することはできません。",visible=False)
        with gr.Row():
            self.restart_btn=gr.Button("もう一回！",scale=0, link="/avery/retry", visible=False)
            
            self.end_btn=gr.Button("やめる",scale=0, visible=False)
            self.confirm_btn=gr.Button("確認",scale=0,link="/avery/new_game", visible=False)
            self.cancel_btn=gr.Button("キャンセル",scale=0, visible=False)

            self.end_btn.click(
                lambda :[gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)], 
                None, 
                [self.end_btn, self.restart_btn, self.confirm_txt, self.confirm_btn, self.cancel_btn]
            )

            self.cancel_btn.click(
                lambda :[gr.update(visible=True), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)], 
                None, 
                [self.end_btn, self.restart_btn, self.confirm_txt, self.confirm_btn, self.cancel_btn]
            )

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

    async def obtain_image(request: gr.Request):
        request = request.request
        leaderboard_id = request.session.get('leaderboard_id', None)
        generation_id = request.session.get('generation_id', None)
        if not leaderboard_id:
            return None
        elif not generation_id:
            return None
        
        original_img = await get_original_images(int(leaderboard_id), request)
        ai_img = await get_interpreted_image(int(generation_id), request)
        similarity = await get_image_similarity(int(generation_id), request)
        
        if similarity:
            similarity = float(similarity.similarity)*100
            if similarity > 80:
                emoji = "🎉"
            elif similarity > 60:
                emoji = "👍"
            elif similarity > 40:
                emoji = "🤔"
            else:
                emoji = "😢"
        similarity_md = "# 類似度: {:^10.2f} {}".format(similarity, emoji)
        return original_img, ai_img, similarity_md
    
    async def load_chat_content(request: gr.Request):
        request = request.request
        generation_id = request.session.get('generation_id', None)
        cur_round = request.session.get('round', None)
        # complete the generation and get the chat
        if generation_id is None:
            raise Exception("Generation not found")
        
        if cur_round is None:
            raise Exception("Round not found")

        if cur_round:
            chat = await get_chat(
                round_id=cur_round['id'],
                request=request,
            )

            if chat:
                check_generated_time = request.session.get("generated_time", 0) < MAX_GENERATION
                show_restart = gr.update(visible=check_generated_time)
                if check_generated_time:
                    show_end = gr.update(visible=True, link=None)
                    restart_value = "もう一回！({:.0f}/{:.0f})".format(MAX_GENERATION - request.session.get("generated_time", 0), MAX_GENERATION)
                else:
                    show_end = gr.update(visible=True, link="/avery/new_game")
                    restart_value = "もう一回！"
                send_msg = gr.update(visible=False)
                md = ""
                md += chat.messages[-2].content.replace("\n", "\n\n")
                md += "\n\n"
                md += chat.messages[-1].content.replace("\n", "\n\n")
                yield convert_history(chat), show_restart, show_end, restart_value,send_msg,send_msg,md
                return
            else:
                yield None

    async def ask_hint( message: str, chat_history: list, request: gr.Request):
        request = request.request
        if message == "":
            return None, chat_history
        if not request.session.get('round', None):
            raise Exception("Round not found")
        round_id = request.session.get('round', None)['id']
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

    with gr.Row():
        with gr.Column(scale=1):
            guidance=Guidance()
            guidance.create_guidance()
            gr.update()

            gr.on(triggers=[guidance.msg.submit,guidance.submit.click],
                    fn=ask_hint,
                    inputs=[guidance.msg, guidance.chat],
                    outputs=[guidance.msg, guidance.chat],
                    queue=False
            )

        with gr.Column(scale=2):
            md = gr.Markdown()

    with gr.Row():
        with gr.Column(scale=1):
            result=Result()
            result.create_result()


    avery_gradio.load(obtain_image, inputs=[], outputs=[result.image, result.ai_image, result.similarity])
    avery_gradio.load(load_chat_content, inputs=[], outputs=[guidance.chat, result.restart_btn, result.end_btn, result.restart_btn,guidance.msg,guidance.submit,md])
    avery_gradio.queue(max_size=128, default_concurrency_limit=50)




