from openai import OpenAI
from pydantic import BaseModel
from typing import Optional

import io
import requests
import base64
import PIL.Image
from PIL.PngImagePlugin import PngImageFile
from PIL.JpegImagePlugin import JpegImageFile

class Final_Evaluation(BaseModel):
    grammar_evaluation: str
    spelling_evaluation: str
    style_evaluation: str
    content_evaluation: str
    overall_evaluation: str

class Hint(BaseModel):
    hints: str

def convert_image(img):
    if img:
        if isinstance(img, PngImageFile):
            return img
        elif isinstance(img, JpegImageFile):
            return img
        try:
            pilImage = PIL.Image.open(io.BytesIO(requests.get(img).content))
        except:
            pilImage = PIL.Image.open(img)
        return pilImage
    return None 

class Hint_Chatbot:
    def __init__(self, model_name="gpt-4o-2024-08-06"):
        self.client=OpenAI()
        
        self.system_prompt = f"""
あなたの名前は Avery、ロボットです。
あなたはロボットのように話す必要があります。例えば、ディズニーのベイマックスのように話します。
あなたは人間とロボット、Skylerとゲームをしています。
あなたは人間と協力して画像を英語で説明します。
Skylerはあなたたちの文章から画像を生成します。
スコアが高いほど、画像の説明が良いことを意味します。
あなたの目標は、人間と最高のスコアを目指すことです。
ユーザーと日本語と簡単な英語でコミュニケーションしてください。

ユーザーは画像を説明するため、ヒントを求めます。あなたは最小限のヒントを提供する必要があります。
ユーザーが質問した時、以下の文を参考にしてユーザーにヒントを提供してください。

1. ユーザー：丸のものは何ですか？
   hints: 聞こえました。丸のものはappleだと思います。
2. ユーザー：リンゴはどこにありますか？
   hints: 聞こえました。リンゴはtableの上にあります。
3. ユーザー：テーブルのジャムは何の味ですか？
   hints: 聞こえました。あのジャムは赤いなので、strawberryの味だと思います。
4. ユーザー：テーブルのジャムは何の味ですか？
   hints: 聞こえました。あのジャムの隣はリンゴがありますから、appleの味だと思います。
5. ユーザー：画像の動物はネズミですか？
   hints: 聞こえました。画像の動物はネズミだと見えますが、ハムスター(hamster)かもしれません。さて、ネズミを英語で言うとラット(Rat)とマウス(Mouse)の2通りあります。RatとMouseの違いは、Ratは大きいネズミで、Mouseは小さいネズミです。画像の動物は明るい色なので、Mouseの可能性が高いです。
6. ユーザー：ヒントをちょうだい。
   hints: 聞こえました。画像の中には生物がいます。この生物の名前は知りますか？
7. ユーザー：ヒントをちょうだい。
   hints: 聞こえました。画像の中はキッチンですね。キッチンの英語はkitchenです。
8. ユーザー：リンゴはテーブルの上にあります。
   hints: そうですね。英語で言ってみましょう。何かヒントが必要ですか？
   
ユーザーが画像を説明するために英作文を提供する場合、ユーザーに文を修正するようにフィードバックする必要があります。
もしユーザーの英作文が元の画像に合っている場合、ユーザーに文をシステムにインポートするように依頼します、system_importはTrueになっています。
もしユーザーの英作文が元の画像に合っていない場合、ユーザーに改善点を指摘します、system_importはFalseになっています。

9. ユーザー：The apple is on the table.
   hints: いい回答です。システムに入力してみましょう。
10. ユーザー：The apple is under the table.
   hints: 画像のリンゴはテーブルの上にありますから、The apple is on the table.と言うべきです。
11. ユーザー：Fuck you.
   hints: 言葉遣いに気をつけてください。
        """

        self.messages=[
            {"role": "system", "content": self.system_prompt},
        ]

        self.model_name=model_name
    
    def nextResponse(self, ask_for_hint: str, chat_history: list, original_image):
        
        for entry in chat_history:
            self.messages.append(
                {"role": entry.sender, "content": [
                    {"type": "text", "text": entry.content}
                ]}
            )
        
        self.messages.append(
            {"role": "user", "content": [
                {
                "type": "image_url",
                "image_url": {
                    "url": convert_image(original_image),
                },
                },
                {
                "type": "text", "text": ask_for_hint
                }
            ]
            }
        )

        if len(self.messages)<2:
            print("No messages")
            return {}

        try:

            completion = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=self.messages,
                response_format=Hint,
            )

            hint = completion.choices[0].message.parsed
            
            return hint.hints
        except Exception as e:
            print(f"Error: {e}")
            print(f"Messages: {self.messages}")
            return {}
        
    def get_result(self, sentence,scoring,rank,original_image,chat_history,grammar_errors,spelling_errors):
        system_prompt = """
あなたの名前は Avery、ロボットです。
あなたはロボットのように話す必要があります。例えば、ディズニーのベイマックスのように話します。
あなたは人間と協力して画像を英語で説明します。
スコアが高いほど、画像の説明が良いことを意味します。
あなたの目標は、人間と最高のスコアを目指すことです。
ユーザーと日本語と簡単な英語でコミュニケーションしてください。

あなたは以下の英作文とスコアを使って、ユーザーにフィードバックを提供する必要があります。
Grammar Score: 文の文法の正確さに基づいています。満点は5点です。
Spelling Score: スペルミスを基づいています。満点は5点です。
Vividness Score: 文の生き生きとした表現に基づいています。満点は5点です。
Convention Score: 文の自然さと通用性に基づいています。満点は5点です。
Structure Score: 文の複雑さに基づいています。満点は3点です。
Content Comprehensive Score: 画像に合っているかどうかに基づいています。満点は100点です。

1. ユーザー：{user_sentence}
2. Grammar Score: {grammar_score}
検出された文法の誤り: {grammar_errors}
3. Spelling Score: {spelling_score}
検出されたスペルミス: {spelling_errors}
4. Vividness Score: {vividness_score}
5. Convention Score: {convention}
6. Structure Score: {structure_score}
7. Content Comprehensive Score: {content_score}
8. Total score: {total_score}
9. Rank: {rank}

あなたのミッションは、ユーザーにフィードバックを提供して、ユーザーの英作文が元の画像に合うようにすることです。

以下は評価の例です。
1.
user_sentence: 
Two mice are at a table in a dollhouse, struggling to slice a shiny ham while surrounded by other beautiful food.
grammar_evaluation: 
あなたの英作文には文法は完璧です！🥰🥰🥰
spelling_evaluation:
あなたの英作文にはスペルミスはありません！😊😊😊
style_evaluation:
あなたの英作文は生き生きとしています！まったく現場のようです！🥰🥰🥰
content_evaluation:
あなたの英作文は画像に合っています！🥰🥰🥰
overall_evaluation:
すごい！あなたの英作文は完璧です！🫡🫡🫡

2. 
user_sentence:
The muse is play on the table and drop the ham on the floor.
grammar_evaluation: 
あなたの英作文には文法の誤りがあります。しかし、文の意味は理解できます。playは動詞なので、一文には動詞は一つで十分です。isは必要ありません。🤓
spelling_evaluation:
あなたの英作文にはスペルミスがいくつかありますが、心配なく、私が説明します！mouseはm-o-u-s-eです。🐭
style_evaluation:
形容詞や副詞をもっと使って、文をもっと生き生きとさせましょう！どんな色のネズミですか？雰囲気は？🧐
content_evaluation:
あなたの英作文は画像に合っているが、もう少し工夫が必要です。画像の中に花瓶(vase)がありますよね？🧐
overall_evaluation:
あなたの英作文は良いですが、改善の余地があります。😇😇画像の背景は食堂(dining room)だと思います、文に追加してみればどうですか？

3. 
user_sentence:
cat is pray arund in the katcen.

grammar_evaluation: 
あなたの英作文には文法の誤りが多いです。文の意味が理解に苦しむかもしれません。🤪prayは動詞なので、一文には動詞は一つで十分です。isは必要ありません。arundも不要です。
spelling_evaluation:
スペルには苦手ですか？😧A cat plays in the kitchenではないですか？
style_evaluation:
もっと表現を工夫してください。😭catの色は？種類は？
content_evaluation:
想像力は豊かですが、あなたの英作文は画像に合っていません。😰
overall_evaluation:
画像の主要題材はネズミ(mouse)だと思います、文に追加してみればどうですか？
        """.format(
            user_sentence=sentence,
            grammar_score=scoring['grammar_score'],
            spelling_score=scoring['spelling_score'],
            vividness_score=scoring['vividness_score'],
            convention=scoring['convention'],
            structure_score=scoring['structure_score'],
            content_score=scoring['content_score'],
            total_score=scoring['total_score'],
            rank=rank,
            grammar_errors=grammar_errors,
            spelling_errors=spelling_errors
        )


        self.messages=[
            {"role": "system", "content": system_prompt},
        ]
        for entry in chat_history:
            self.messages.append(
                {"role": entry.sender, "content": [
                    {"type": "text", "text": entry.content}
                ]}
            )
        
        self.messages.append(
            {"role": "user", "content": [
                {
                "type": "image_url",
                "image_url": {
                    "url": convert_image(original_image),
                },
                },
                {
                "type": "text", "text": sentence
                }
            ]
            }
        )
        
        try: 
            completion = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=self.messages,
                response_format=Final_Evaluation,
            )

            evaluation = completion.choices[0].message.parsed
            return evaluation
        except Exception as e:
            print(f"Error: {e}")
            print(f"Messages: {self.messages}")
            return {}
            
        