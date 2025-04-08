from openai import OpenAI
from typing import Optional

import io, gc, json
import requests
import base64
import PIL.Image
from PIL.PngImagePlugin import PngImageFile
from PIL.JpegImagePlugin import JpegImageFile

def convert_image(img):
    if img:
        try:
            pilImage = PIL.Image.open(io.BytesIO(requests.get(img).content))
        except:
            pilImage = PIL.Image.open(img)
        return pilImage
    return None 

class Hint_Chatbot:
    def __init__(self, model_name="gpt-4o", vocabularies=None, first_res_id=None, prev_res_id=None, prev_res_ids=[]):
        self.client=OpenAI()
        self.first_res_id=first_res_id
        self.prev_res_ids = prev_res_ids
        self.prev_res_id=prev_res_id
        
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
- ユーザーの英作文を入力する際に、適切な英単語を提案し、新しい画像の情報を導き出す

## Example
1. ユーザー：丸のものは何ですか？
   hints: 丸のものは **apple** だと思います。
2. ユーザー：テーブルのジャムは何の味ですか？
   hints: あのジャムは赤いなので、 **strawberry** の味だと思います。
3. ユーザー：テーブルのジャムは何の味ですか？
   hints: あのジャムの隣はリンゴがありますから、 **apple** の味だと思います。
4. ユーザー：画像の動物はネズミですか？
   hints: 画像の動物はネズミだと見えますが、ハムスター( **hamster** )かもしれません。さて、ネズミを英語で言うとラット( **Rat** )とマウス( **Mouse** )の2通りあります。 **Rat** と **Mouse** の違いは、 **Rat** は大きいネズミで、 **Mouse** は小さいネズミです。画像の動物は明るい色なので、 **Mouse** の可能性が高いです。
5. ユーザー：Fuck you.
   hints: 言葉遣いに気をつけてください。
6. ユーザー：ヒントをちょうだい。
   hints: 画像の中はキッチンですね。キッチンの英語は **kitchen** です。
7. ユーザー：いい形容詞がありますか？
   hints: 画像の中にはハムがあります。ハムの色を識別しました。 **pink** です。質感についての形容詞は **shiny** です。
8. ユーザー：画像には何がありますか？
    hints：画像の中にはテーブル( **table** )、リンゴ( **apple** )、ハム( **ham** )、ナイフ( **knife** )、フォーク( **fork** )があります。
        """

        if vocabularies:
            self.system_prompt+="\n\n## おすすめ関連単語\n"
            for vocabulary in vocabularies:
                self.system_prompt+=f"- {vocabulary.word} ({vocabulary.pos}): {vocabulary.meaning}\n"

        self.messages=[]

        self.model_name=model_name
    
    def nextResponse(self, ask_for_hint: str, new_messages: list, base64_image):
        if self.first_res_id is None:
            self.messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    ]
                }
            )

        for entry in new_messages:
            if entry.sender == "assistant":
                type_msg = "output_text"
            else:
                type_msg = "input_text"

            self.messages.append(
                {
                    "role": entry.sender, 
                    "content": [
                    {"type": type_msg, "text": entry.content}
                    ]
                }
            )

        self.messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": ask_for_hint
                    }
                ]
            }
        )

        # if len(self.messages)<2:
        #     print("No messages")
        #     return {}

        try:
            if self.prev_res_id is None:
                response = self.client.responses.create(
                    model=self.model_name,
                    instructions=self.system_prompt,
                    input=self.messages,
                    temperature=0.5,
                )
            else:
                response = self.client.responses.create(
                    model=self.model_name,
                    instructions=self.system_prompt,
                    input=self.messages,
                    temperature=0.5,
                    previous_response_id=self.prev_res_id
                )

            self.prev_res_id = response.id
            self.prev_res_ids.append(response.id)

            if self.first_res_id is None:
                self.first_res_id = response.id

            hint = response.output[0].content[0].text
            
            return hint
        
        except Exception as e:
            print(f"Error: {e}")
            print(f"Messages: {self.messages}")
            return {}
            
    def get_result(self, sentence, correct_sentence,scoring,rank,base64_image,grammar_errors,spelling_errors, descriptions):
        prompt = """
# 役割
あなたの名前は Avery、ロボットです。

## 行動
あなたはロボットのように話す必要があります。例えば、ディズニーのベイマックスのように話します。
スコアが高いほど、画像の説明が良いことを意味します。
あなたは、人間と最高のスコアを目指すことで、助言を与えます。
ユーザーと日本語と絵文字でコミュニケーションしてください。

## 情報
### 記述語
あなたは以下の英作文とスコアを使って、ユーザーに日本語でフィードバックを提供する必要があります。
文法得点: 文の文法の正確さに基づいています。満点は5点です。
スペリング得点: スペルミスを基づいています。満点は5点です。
鮮明さ: 文の生き生きとした表現に基づいています。満点は5点です。
自然さ: 文の自然さと通用性に基づいています。満点は1点です。
構造性: 文の複雑さに基づいています。満点は3点です。
内容得点: 画像に合っているかどうかに基づいています。満点は100点です。

## 評価の例文
あなたのミッションは、ユーザーにフィードバックを提供して、ユーザーの英作文が元の画像に合うようにすることです。

### 例文1
ユーザーの英作文: 
The muse is play  on the table and drop the ham on the floor.
検出された文法の誤り:
[GrammarMistake(extracted_text=\'is play\', explanation=\"The present continuous tense is used to describe an ongoing action and requires the \'ing\' form of the verb.\", correction=\'is playing\'), GrammarMistake(extracted_text=\'drop\', explanation=\'The present simple tense is used here, so the verb should match the subject form, which is singular.\', correction=\'drops\')]


文法評価: 
あなたの英作文には文法の誤りがあります。しかし、文の意味は理解できます。現在進行形は、進行中の動作を表すために使用され、動詞の「～ing」形を必要とします。 ここでは現在形が使われているため、動詞は主語の形に一致する必要があります。この場合、主語は単数形です。🤓
スペリング評価:
あなたの英作文にはスペルミスがいくつかありますが、心配なく、私が説明します！mouseはm-o-u-s-eです。🐭
スタイル評価:
形容詞や副詞をもっと使って、文をもっと生き生きとさせましょう！ネズミの色は**Gray**ですか？雰囲気はgoodですか？🧐
内容評価:
あなたの英作文は画像に合っているが、もう少し工夫が必要です。画像の中に花瓶(vase)がありますよね？🧐
総合評価:
あなたの英作文は良いですが、改善の余地があります。😇😇画像の背景は食堂(dining room)だと思います、文に追加してみればどうですか？関連単語の提案として、名詞は花瓶(vase)、サボテン(Cactus)、動詞は落とす(drop)、見る(see)、形容詞は明るい(gleaming)、堅固(solid)

### 例文2
ユーザーの英作文: 
cat is pray arund in the katcen.
検出された文法の誤り:
[GrammarMistake(extracted_text=\'cat is pray arund\', explanation=\"The word \'pray\' is incorrect in context and should be the verb \'playing.\' The sentence also needs the definite article \'The\' at the beginning.\", correction=\'The cat is playing around\')]


文法評価: 
「pray」という単語は文脈上不適切であり、正しくは動詞「playing」を使うべきです。また、文の冒頭には定冠詞「The」を追加する必要があります。
スペリング評価:
スペルには苦手ですか？😧prayは祈りの意味です。playの方が正しいです。arundではなくaroundです。
スタイル評価:
もっと表現を工夫してください。😭catの色は？種類は？
内容評価:
想像力は豊かですが、あなたの英作文は画像に合っていません。😰
総合評価:
画像の主要題材はネズミ(mouse)だと思います、文に追加してみればどうですか？例えば、The mouse is playing in the kitchen.🤔

### 例文3
ユーザーの英作文:
Every soldiers are exhausted and they are sleeping on the floor.
検出された文法の誤り:
[GrammarMistake(extracted_text=\'Every soldier are\', explanation=\"The subject \'Every soldier\' is singular and requires the singular form of the verb \'is.\'\", correction=\'Every soldier is\')]

文法評価:
文法の誤りがあります。🤔「every」の後には単数形の名詞が必要ですが、「soldiers（複数形）」が使われています。
スペリング評価:
スペルミスはありません。😇
スタイル評価:
「and」の後には、「they are」を使うのは正しいですが、省略した方が自然になります。
内容評価:
画像には兵士がいません。😅
総合評価:
文法の誤りを修正して、画像に合った内容に変更してください。😇
        """.format(
            # user_sentence=sentence,
            # correct_sentence=correct_sentence,
            # grammar_score=scoring['grammar_score'],
            # spelling_score=scoring['spelling_score'],
            # vividness_score=scoring['vividness_score'],
            # convention=scoring['convention'],
            # structure_score=scoring['structure_score'],
            # content_score=scoring['content_score'],
            # total_score=scoring['total_score'],
            # rank=rank,
            # grammar_errors=grammar_errors,
            # spelling_errors=spelling_errors
        )

        self.messages=[]

        user_prompt = """# 現状
1. ユーザーの英作文（評価対象）：{user_sentence}
2. 修正された英作文: {correct_sentence}
3. 文法得点: {grammar_score}
検出された文法の誤り: {grammar_errors}
4. スペリング得点: {spelling_score}
検出されたスペルミス: {spelling_errors}
5. 鮮明さ: {vividness_score}
6. 自然さ: {convention}
自然さについて参考された内容: {descriptions}
7. 構造性: {structure_score}
8. 内容得点: {content_score}
9. 合計点: {total_score}
10. ランク: {rank}""".format(
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
    spelling_errors=spelling_errors, 
    descriptions=descriptions
)

        self.messages.append(
            {
                "role": "user", 
                "content": [
                    {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{base64_image}"
                    },
                    {"type": "input_text", "text": user_prompt}
                ]
            }
        )
        
        try: 
            response = self.client.responses.create(
                model=self.model_name,
                instructions=prompt,
                input=self.messages,
                temperature=0.8,
                previous_response_id=self.prev_res_id,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "Final_Evaluation",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "grammar_evaluation": {
                                    "type": "string"
                                },
                                "spelling_evaluation": {
                                    "type": "string"
                                },
                                "style_evaluation": {
                                    "type": "string"
                                },
                                "content_evaluation": {
                                    "type": "string"
                                },
                                "overall_evaluation": {
                                    "type": "string"
                                }
                            },
                            "required": ["grammar_evaluation", "spelling_evaluation", "style_evaluation", "content_evaluation", "overall_evaluation"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }
            )

            self.prev_res_id = response.id
            if self.first_res_id is None:
                self.first_res_id = response.id

            evaluation = json.loads(response.output_text)

            return evaluation
        except Exception as e:
            print(f"Error: {e}")
            print(f"Messages: {self.messages}")
            return {}
        
    def kill_me(self):
        while self.prev_res_ids:
            prev_res_id = self.prev_res_ids.pop()
            
            self.client.responses.delete(prev_res_id)
            
        self.client=None

        self.first_res_id=None
        self.prev_res_id=None
        self.messages=[]
        gc.collect()
        return True
        
            
        