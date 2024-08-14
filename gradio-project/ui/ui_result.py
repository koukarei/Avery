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
        
    def get_params(self,cur_round:Round,game_data_dict:dict):
        effectiveness,grammar,vocab,total,rank,ai_play=cur_round.total_score(
            sentence=game_data_dict['sentence'],
            corrected_sentence=game_data_dict['corrected_sentence'],
            original_picture_path=game_data_dict['original_picture_path'],
            story=game_data_dict['story']
        )
        game_data_dict['ai_play']=ai_play
        game_data_dict['effectiveness_score']=round(effectiveness*100,2)
        game_data_dict['semantic_score']=round(grammar*100,2)
        game_data_dict['vocab_score']=round(vocab*100,2)
        game_data_dict['total']=round(total*100,2)
        game_data_dict['rank']=rank
        self.ai_play=ai_play
        self.effectiveness_score=game_data_dict['effectiveness_score']
        self.grammar_score=game_data_dict['semantic_score']
        self.vocab_score=game_data_dict['vocab_score']
        self.total_score=game_data_dict['total']
        self.rank_level=game_data_dict['rank']

        return game_data_dict

    def create_result_tab(self):
        example='\n'.join(
            ["{} : {}".format(j+1,k) for j,k in enumerate(self.ai_play)]
        )
        self.example=gr.Textbox(example,label='Example',interactive=False)
        self.effectiveness=gr.Textbox(self.effectiveness_score,label='Effectiveness',interactive=False)
        self.grammar=gr.Textbox(self.grammar_score,label='Grammar',interactive=False)
        self.vocab=gr.Textbox(self.vocab_score,label='Vocabulary',interactive=False)
        self.total=gr.Textbox(self.total_score,label='Total',interactive=False)
        self.rank=gr.Textbox(self.rank_level,label='Rank',interactive=False)
        with gr.Row():
            self.restart_btn=gr.Button("Help more!",scale=0)
            self.survey_btn=gr.Button("Survey",scale=0,link='https://forms.gle/KbXzJPuvP9uts12p8')

    def get_data(self,game_data_dict:dict):
        
        example='\n'.join(
            ["{} : {}".format(j+1,k) for j,k in enumerate(game_data_dict['ai_play'])]
        )
        return example,game_data_dict['effectiveness_score'],game_data_dict['semantic_score'],game_data_dict['vocab_score'],game_data_dict['total'],game_data_dict['rank']
            
    def save_image(self,game_data_dict:dict,cur_round:Round):
        quality=95
        optimize=True
        progressive=True
        round_id=game_data_dict['round_id']
        original_picture=game_data_dict['original_picture']
        interpreted_picture=game_data_dict['interpreted_picture']
        self.original_picture_path='data/Original Picture/'+round_id+'.jpg'
        if os.path.exists(self.original_picture_path):
            round_id=cur_round.set_id()
            game_data_dict['round_id']=round_id
            self.original_picture_path='data/Original Picture/'+round_id+'.jpg'
        self.interpreted_picture_path='data/Interpreted Picture/'+round_id+'.jpg'

        original_picture.save(
            self.original_picture_path,
            quality=quality,
            optimize=optimize,
            progressive=progressive,
        )
        interpreted_picture.save(
            self.interpreted_picture_path,
            quality=quality,
            optimize=optimize,
            progressive=progressive,
        )
        return game_data_dict

    def log_result(self,game_data_dict:dict):

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
                
        example='\n'.join(
            ["{} : {}".format(j,k) for j,k in enumerate(game_data_dict['ai_play'])]
        )
        with open('data/Result/result.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            new_row=[
                game_data_dict['round_id'],
                self.original_picture_path,
                self.interpreted_picture_path,
                game_data_dict['sentence'],
                game_data_dict['corrected_sentence'],
                example,
                game_data_dict['chat_history'],
                game_data_dict['effectiveness_score'],
                game_data_dict['semantic_score'],
                game_data_dict['vocab_score'],
                game_data_dict['total'],
                game_data_dict['rank']
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