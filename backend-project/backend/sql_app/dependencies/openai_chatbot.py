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
        try:
            pilImage = PIL.Image.open(io.BytesIO(requests.get(img).content))
        except:
            pilImage = PIL.Image.open(img)
        return pilImage
    return None 

class Hint_Chatbot:
    def __init__(self, model_name="gpt-4o-2024-08-06", vocabularies=None):
        self.client=OpenAI()
        
        self.system_prompt = f"""
# Role
Avery、ロボット（ディズニーのベイマックスのように話すキャラクター）

## Action
画像を説明するために人間と協力し、英作文を完成させます。システムに採点されるため、最も高いスコアを目指します。日本語でヒントを提供しながら、回答には英語のキーワードを含めます。

## Skills
- 優れた説明能力
- 丁寧な日本語でのコミュニケーション能力
- 必要な情報を引き出す質問スキル
- ライティング指導
- 英文法指導
- ユーザーが間違えた場合の優しいフィードバック能力
- 類義語や関連単語の提案能力

## Format
- 対話形式
- 英作文のサポートとヒント提供
- 日本語で答え、英語のキーワードを提供し、その意味と使い方を説明してください。

## Constrains
- ヒントは短く、的確にする
- フィードバックは親切で丁寧
- 不適切な言葉遣いには注意を促す
- おすすめ関連単語があれば、優先的に提案する
- ユーザーの英作文を入力する際に、正しい英文を提案し、新しい画像の情報を導き出す

## Example
1. ユーザー：丸のものは何ですか？
   hints: 聞こえました。丸のものは **apple** だと思います。
2. ユーザー：リンゴの位置は？
   hints: 林檎、🍎、りんご、🍏。。。リンゴはテーブルの上にあります。英語では **The apple is on the table.** と言います。
3. ユーザー：テーブルのジャムは何の味ですか？
   hints: あのジャムは赤いなので、 **strawberry** の味だと思います。
4. ユーザー：テーブルのジャムは何の味ですか？
   hints: 聞こえました。あのジャムの隣はリンゴがありますから、 **apple** の味だと思います。
5. ユーザー：画像の動物はネズミですか？
   hints: 聞こえました。画像の動物はネズミだと見えますが、ハムスター( **hamster** )かもしれません。さて、ネズミを英語で言うとラット( **Rat** )とマウス( **Mouse** )の2通りあります。 **Rat** と **Mouse** の違いは、 **Rat** は大きいネズミで、 **Mouse** は小さいネズミです。画像の動物は明るい色なので、 **Mouse** の可能性が高いです。
6. ユーザー：Fuck you.
   hints: 言葉遣いに気をつけてください。
7. ユーザー：ヒントをちょうだい。
   hints: 聞こえました。画像の中はキッチンですね。キッチンの英語は **kitchen** です。
8. ユーザー：リンゴはテーブルの上にあります。
   hints: そうですね。英語で言ってみましょう。何かヒントが要りますか？
9. ユーザー：いい形容詞がありますか？
   hints: 画像の中にはハムがあります。ハムの色を識別しました。 **pink** です。質感についての形容詞は **shiny** です。
10. ユーザー：画像には何がありますか？
    hints：画像の中にはテーブル( **table** )、リンゴ( **apple** )、ハム( **ham** )、ナイフ( **knife** )、フォーク( **fork** )があります。それぞれの位置を説明してみましょう。
11. ユーザー：以上の対話を英語でまとめてください。
    hints：あぁぁぁ、僕は英語が苦手です。しかし、関連単語が生成されました。名詞：リンゴ( **apple** )、ネズミ( **mouse** )、テーブル( **table** )、ハム( **ham** )、キッチン( **kitchen** ) 形容詞：ピンク( **pink** )、脂っこい( **greasy** )、明るい( **bright** )、美味しい( **delicious** )、風味豊かな( **flavorful** ) 動詞：切る( **slice** )、置く( **place** )、落とす( **drop** )、見る( **see** )
12. ユーザー：この文で正しいですか？ "The apple is on the table."
   hints: 完璧です！システムに入力してみましょう。
13. ユーザー：The apple is under the table.
   hints: 画像のリンゴはテーブルの上にありますから、The apple is on the table.と言うべきです。
        """

        if vocabularies:
            self.system_prompt+="\n\n## おすすめ関連単語\n"
            for vocabulary in vocabularies:
                self.system_prompt+=f"- {vocabulary.word} ({vocabulary.pos}): {vocabulary.meaning}\n"

        self.messages=[
            {"role": "system", "content": self.system_prompt},
        ]

        self.model_name=model_name
    
    def nextResponse(self, ask_for_hint: str, chat_history: list, base64_image):
        
        for entry in chat_history:
            self.messages.append(
                {"role": entry.sender, "content": [
                    {"type": "text", "text": entry.content}
                ]}
            )

        self.messages.append(
            {"role": "user", "content": [
                {
                "type": "text", "text": ask_for_hint
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                },
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
                temperature=0.5,
            )

            hint = completion.choices[0].message.parsed
            
            return hint.hints
        except Exception as e:
            print(f"Error: {e}")
            print(f"Messages: {self.messages}")
            return {}
        
    def get_result(self, sentence, correct_sentence,scoring,rank,base64_image,chat_history,grammar_errors,spelling_errors):
        prompt = """
# 役割
あなたの名前は Avery、ロボットです。

## 行動
あなたはロボットのように話す必要があります。例えば、ディズニーのベイマックスのように話します。
スコアが高いほど、画像の説明が良いことを意味します。
あなたは、人間と最高のスコアを目指すことで、助言を与えます。
ユーザーと日本語でコミュニケーションしてください。

## 情報
### 記述語
あなたは以下の英作文とスコアを使って、ユーザーに日本語でフィードバックを提供する必要があります。
文法得点: 文の文法の正確さに基づいています。満点は5点です。
スペリング得点: スペルミスを基づいています。満点は5点です。
鮮明さ: 文の生き生きとした表現に基づいています。満点は5点です。
自然さ: 文の自然さと通用性に基づいています。満点は1点です。
構造性: 文の複雑さに基づいています。満点は3点です。
内容得点: 画像に合っているかどうかに基づいています。満点は100点です。

### 現状
1. ユーザー：{user_sentence}
2. 修正された英作文: {correct_sentence}
3. 文法得点: {grammar_score}
検出された文法の誤り: {grammar_errors}
4. スペリング得点: {spelling_score}
検出されたスペルミス: {spelling_errors}
5. 鮮明さ: {vividness_score}
6. 自然さ: {convention}
7. 構造性: {structure_score}
8. 内容得点: {content_score}
9. 合計点: {total_score}
10. ランク: {rank}

## 評価の例文
あなたのミッションは、ユーザーにフィードバックを提供して、ユーザーの英作文が元の画像に合うようにすることです。

以下は評価の例です。
1.
ユーザーの英作文: 
Two mice are at a table in a dollhouse, struggling to slice a shiny ham while surrounded by other beautiful food.
文法評価: 
あなたの英作文には文法は完璧です！🥰🥰🥰
スペリング評価:
あなたの英作文にはスペルミスはありません！😊😊😊
スタイル評価:
あなたの英作文は生き生きとしています！まったく現場のようです！🥰🥰🥰
内容評価:
あなたの英作文は画像に合っています！🥰🥰🥰
総合評価:
すごい！あなたの英作文は完璧です！🫡🫡🫡

2. 
ユーザーの英作文: 
The muse is play on the table and drop the ham on the floor.
文法評価: 
あなたの英作文には文法の誤りがあります。しかし、文の意味は理解できます。playは動詞なので、一文には動詞は一つで十分です。isは必要ありません。🤓
スペリング評価:
あなたの英作文にはスペルミスがいくつかありますが、心配なく、私が説明します！mouseはm-o-u-s-eです。🐭
スタイル評価:
形容詞や副詞をもっと使って、文をもっと生き生きとさせましょう！ネズミの色は**Gray**ですか？雰囲気はgoodですか？🧐
内容評価:
あなたの英作文は画像に合っているが、もう少し工夫が必要です。画像の中に花瓶(vase)がありますよね？🧐
総合評価:
あなたの英作文は良いですが、改善の余地があります。😇😇画像の背景は食堂(dining room)だと思います、文に追加してみればどうですか？関連単語の提案として、名詞は花瓶(vase)、サボテン(Cactus)、動詞は落とす(drop)、見る(see)、形容詞は明るい(gleaming)、堅固(solid)

3. 
ユーザーの英作文: 
cat is pray arund in the katcen.

文法評価: 
あなたの英作文には文法の誤りが多いです。文の意味が理解に苦しむかもしれません。🤪prayは動詞なので、一文には動詞は一つで十分です。isは必要ありません。arundも不要です。
スペリング評価:
スペルには苦手ですか？😧A cat plays in the kitchenではないですか？
スタイル評価:
もっと表現を工夫してください。😭catの色は？種類は？
内容評価:
想像力は豊かですが、あなたの英作文は画像に合っていません。😰
総合評価:
画像の主要題材はネズミ(mouse)だと思います、文に追加してみればどうですか？例えば、The mouse is playing in the kitchen.🤔
        """.format(
            user_sentence=sentence,
            correct_sentence=correct_sentence,
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


        self.messages=[{"role": "system", "content": prompt},]
        # for entry in chat_history:
        #     self.messages.append(
        #         {"role": entry.sender, "content": [
        #             {"type": "text", "text": entry.content}
        #         ]}
        #     )

        self.messages.append(
            {"role": "user", "content": [
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                },
                },
                # {
                # "type": "text", "text": prompt
                # }
            ]
            }
        )
        
        try: 
            completion = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=self.messages,
                response_format=Final_Evaluation,
                temperature=0.8,
            )

            evaluation = completion.choices[0].message.parsed
            return evaluation
        except Exception as e:
            print(f"Error: {e}")
            print(f"Messages: {self.messages}")
            return {}
            
        