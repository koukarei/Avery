import gradio as gr
from dependencies.score import Score
from dependencies.round import Round
import os, shutil
from PIL import Image
import csv

def save_image_filepath(filename: str,filepath: str):
    print(filepath)
    # イメージを保存
    shutil.copyfile(filepath, 'data/Interpreted Image/'+filename)
    pass

class Result:
    def __init__(self):
        # self.score=Score()
        # self.vocab=None
        # self.grammar=None
        # self.communication=None
        # self.total=None
        # self.rank=None
        # self.leaderboard_btn=None
        pass
        
    def get_params(self,round:Round):
        self.round=round
        self.effectiveness=round.cosine_similarity()*100
        self.grammar=round.semantic_similarity()*100
        self.vocab=round.vocab_difficulty()*100
        self.total=round.total_score()*100
        self.rank=round.rank()

    def create_result_tab(self):
        example='\n'.join(self.round.ai_play)
        self.example=gr.Markdown(f"""## Example
                                 {example}""")
        self.effectiveness=gr.Textbox(self.effectiveness,label='Effectiveness',interactive=False)
        self.grammar=gr.Textbox(self.grammar,label='Grammar',interactive=False)
        self.vocab=gr.Textbox(self.vocab,label='Vocabulary',interactive=False)
        self.total=gr.Textbox(self.total,label='Total',interactive=False)
        self.rank=gr.Textbox(self.rank,label='Rank',interactive=False)
        self.restart_btn=gr.Button("Help more!",scale=0)

    def save_image(self):
        quality=95
        optimize=True
        progressive=True
        
        self.original_picture_path='data/Original Picture/'+self.round.id+'.jpg'
        if os.path.exists(self.original_picture_path):
            self.round.set_id()
            self.original_picture_path='data/Original Picture/'+self.round.id+'.jpg'
        self.interpreted_picture_path='data/Interpreted Picture/'+self.round.id+'.jpg'

        self.round.original_picture.save(
            self.original_picture_path,
            quality=quality,
            optimize=optimize,
            progressive=progressive,
        )
        self.round.interpreted_picture.save(
            self.interpreted_picture_path,
            quality=quality,
            optimize=optimize,
            progressive=progressive,
        )

    def log_result(self):

        fieldname=[
            'id',
            'original_picture_path',
            'interpreted_picture_path',
            'sentence',
            'corrected_sentence',
            'ai_play',
            'chat_history',
            'effectiveness',
            'grammar',
            'vocab',
            'total',
            'rank'
        ]
        if not os.path.exists('data/Result'):
            os.makedirs('data/Result')
        if not os.path.exists('data/Result/result.csv'):
            with open('data/Result/result.csv', 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldname)
                writer.writeheader()
                contents=[]
        with open('data/Result/result.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            new_row=[
                self.round.id,
                self.original_picture_path,
                self.interpreted_picture_path,
                self.round.sentence,
                self.round.corrected_sentence,
                self.round.ai_play,
                self.round.chat_history,
                self.effectiveness.value,
                self.grammar.value,
                self.vocab.value,
                self.total.value,
                self.rank.value
            ]
            writer.writerow(new_row)


    # def ssim_ai_behavior(self,img):
    #     self.score.ssim_ai_behavior(img=img)

    # def create_result(self,original_img,checked_img,keywords,original_sentence,checked_sentence):
    #     self.score.set_Grammar(original_sentence,checked_sentence)
    #     self.score.set_Vocabulary([k['name'] for k in keywords if k in checked_sentence.split()])
    #     self.score.set_EffectiveCom(original_img=original_img,interpreted_img=checked_img)

    #     self.vocab=gr.Textbox(self.score.Vocabulary,label='Vocabulary',interactive=False)
    #     self.grammar=gr.Textbox(self.score.Grammar,label='Grammar',interactive=False)
    #     self.communication=gr.Textbox(self.score.EffectiveCom,label='Communication',interactive=False)
    #     self.total=gr.Textbox(self.score.total,label='Total',interactive=False)
    #     self.rank=gr.Textbox(self.score.Rank,label='Rank',interactive=False)
    #     self.leaderboard_btn=gr.Button("Leaderboard",scale=0)
    #     return self.vocab,self.grammar,self.communication,self.total,self.rank,self.leaderboard_btn