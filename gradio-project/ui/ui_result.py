import gradio as gr
from dependencies.score import Score
import os, shutil
from PIL import Image

def save_image_filepath(filename: str,filepath: str):
    print(filepath)
    # イメージを保存
    shutil.copyfile(filepath, 'data/Interpreted Image/'+filename)
    pass

class Result:
    def __init__(self):
        self.score=Score()
        self.vocab=None
        self.grammar=None
        self.communication=None
        self.total=None
        self.rank=None
        self.leaderboard_btn=None

    def ssim_ai_behavior(self,img):
        self.score.ssim_ai_behavior(img=img)

    def create_result(self,original_img,checked_img,keywords,original_sentence,checked_sentence):
        self.score.set_Grammar(original_sentence,checked_sentence)
        self.score.set_Vocabulary([k['name'] for k in keywords if k in checked_sentence.split()])
        self.score.set_EffectiveCom(original_img=original_img,interpreted_img=checked_img)

        self.vocab=gr.Textbox(self.score.Vocabulary,label='Vocabulary',interactive=False)
        self.grammar=gr.Textbox(self.score.Grammar,label='Grammar',interactive=False)
        self.communication=gr.Textbox(self.score.EffectiveCom,label='Communication',interactive=False)
        self.total=gr.Textbox(self.score.total,label='Total',interactive=False)
        self.rank=gr.Textbox(self.score.Rank,label='Rank',interactive=False)
        self.leaderboard_btn=gr.Button("Leaderboard",scale=0)
        return self.vocab,self.grammar,self.communication,self.total,self.rank,self.leaderboard_btn