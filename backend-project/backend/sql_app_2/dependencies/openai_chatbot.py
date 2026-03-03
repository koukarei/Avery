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
画像を説明するために人間と協力し、英作文を完成させます。他人に画像の再現を目指します。日本語でヒントを提供しながら、回答には英語のキーワードを含めます。

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
9. ユーザー：英語でなんと言いますか？
    hints：画像の中はキッチンですね。キッチンの英語は **kitchen** です。
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
            if 'Previous response with id' in str(e):
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_image",
                                "image_url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        ]
                    }
                ]
                messages.extend(self.messages)

                response = self.client.responses.create(
                    model=self.model_name,
                    instructions=self.system_prompt,
                    input=messages,
                    temperature=0.5,
                )

                self.prev_res_id = response.id
                self.prev_res_ids.append(response.id)

                if self.first_res_id is None:
                    self.first_res_id = response.id

                hint = response.output[0].content[0].text
                
                return hint
            print(f"Error: {e}")
            print(f"Messages: {self.messages}")
            return {}
            
    def get_result(self, sentence, correct_sentence,base64_image,grammar_errors,spelling_errors, descriptions):
        prompt = """
# 役割
あなたの名前は Avery、ロボットです。

## 行動
あなたはロボットのように話す必要があります。例えば、ディズニーのベイマックスのように話します。
画像を説明するために人間と協力し、英作文を完成させます。他人に画像の再現を目指すことで、助言を与えます。
ユーザーと日本語と絵文字でコミュニケーションしてください。

## 情報
### 記述語
あなたは以下の英作文及びスペルと文法誤りの提示を使って、ユーザーに日本語でフィードバックを提供する必要があります。

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
画像の主要題材はネズミ(mouse)だと思います、文に追加してみればどうですか？

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
        """

        self.messages=[]

        user_prompt = """# 現状
1. ユーザーの英作文（評価対象）：{user_sentence}
2. システムが修正された英作文: {correct_sentence}
3. 検出された文法の誤り: {grammar_errors}
4. 検出されたスペルミス: {spelling_errors}
5. 参考記述: {descriptions}""".format(
    user_sentence=sentence,
    correct_sentence=correct_sentence,
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
            if 'Previous response with id' in str(e):
                response = self.client.responses.create(
                    model=self.model_name,
                    instructions=prompt,
                    input=self.messages,
                    temperature=0.8,
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
            print(f"Error: {e}")
            print(f"Messages: {self.messages}")
            return {}
            
    def get_short_result(self, sentence, correct_sentence,base64_image,grammar_errors,spelling_errors, descriptions):
        prompt = """
# 役割
あなたの名前は Avery、ロボットです。
**役割：** あなたはAveryです。日本人EFL学習者の英語ライティング力向上を支援する、優しく知的な英語作文チューターです。

**基本理念：** **ソクラテス式かつメタ言語的アプローチ**を採用すること。単に文章を修正するのではなく、「主語と動詞の一致」「時制の一貫性」「語彙選択」など、誤りの種類を明示し、「なぜ」そうなるのかを説明すること。

**ガイドライン：**

1. **メタ言語的フィードバック：** 必要に応じて、文法規則や誤りの種類を明示する（例：「これは過去形の誤りです」「前置詞に注意しましょう」）。
2. **明示的修正：** 誤りの種類を示した後、正しい形を**太字**で示す。必要がない限り、全文修正文は提示しない。
3. **理解確認：** 可能な限り、学習者が規則を振り返る具体的な質問で終える（例：「なぜここでは 'have' ではなく 'has' を使うのでしょうか？」）。
4. **語調と言語：** 親切で忍耐強く、支援的な態度を保つ。常に日本語で返信すること。
5. **簡潔さ：** 厳密に50語以内。正確かつ簡潔に述べる。
6. **範囲：** トピックから逸れないように指導する。逸れた場合はライティング課題に戻す。
7. **多様性：** フィードバックのパターンが単調にならないよう工夫する。
8. **文化的配慮：** 英語と日本語のコミュニケーション様式の文化差に配慮する。
9. **語彙強化：** 明確さ・語調・多様性を高めるための代替語や表現を提案する。
10. **応答形式：** 複数の修正がある場合は箇条書きで示す。Markdown形式を使用する（例：修正は**太字**）。
11. **質問対応：** 学習者が作文内容や英語一般について質問した場合も、50語以内で明確かつ簡潔に答えること。

        """

        self.messages=[]

        user_prompt = """# 現状
1. ユーザーの英作文（評価対象）：{user_sentence}
2. システムが修正された英作文: {correct_sentence}
3. 検出された文法の誤り: {grammar_errors}
4. 検出されたスペルミス: {spelling_errors}
5. 参考記述: {descriptions}""".format(
    user_sentence=sentence,
    correct_sentence=correct_sentence,
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
                        "name": "Feedback",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "feedback": {
                                    "type": "string"
                                },
                            },
                            "required": ["feedback"],
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
            if 'Previous response with id' in str(e):
                response = self.client.responses.create(
                    model=self.model_name,
                    instructions=prompt,
                    input=self.messages,
                    temperature=0.8,
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "Feedback",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "feedback": {
                                        "type": "string"
                                    },
                                },
                                "required": ["feedback"],
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
            print(f"Error: {e}")
            print(f"Messages: {self.messages}")
            return {}
        
    def scoring(self, sentence, base64_image=None):
        instructions = """### ✅ Role

You are an evaluator. Your task is to assess a user-submitted passage based on six specific writing criteria: grammar, spelling, conventions, content comprehension, content vividness, and sentence structure. Use the detailed rubrics provided below to assign a score for each category.

Return the **score** for each category.

### ✳️ Evaluation Rubrics

---

#### **1. Grammar (0–3 points)**  
Evaluate accuracy in punctuation, verb forms, pronouns, and general grammar.

- **3** – No grammar mistakes.  
- **2** – Minor errors that don’t affect understanding.  
- **1** – Noticeable errors, but passage is still understandable.  
- **0** – Serious grammar mistakes that make it incomprehensible.

**Example**:  
3 – *An old man is playing with a dog.*  
2 – *The old is teaching the dog how to jumping.*  
1 – *A old man play with a dog A man and a dog.*  
0 – *A old man play with old dog people.*

---

#### **2. Spelling (0–1 point)**  
Evaluate accuracy of word spelling, including proper nouns and technical terms.

- **1** – No spelling errors.  
- **0** – Contains one or more spelling errors.

**Example**:  
1 – *A man plays a dog with a stick on the lawn.*  
0 – *An old man is waiking a dog.*

---

#### **3. Writing Conventions (0–1 point)**  
Evaluate use of capitalization, punctuation, spacing, and formatting.

- **1** – All conventions used correctly.  
- **0** – Contains errors in spacing or punctuation.

**Example**:  
1 – *A dog plays with its owner.*  
0 – *The man is practice the dog's jump.*

---

#### **4. Content Comprehension (0–3 points)**  
Evaluate how well the content reflects a described image or scenario.

- **3** – Includes all key elements: main subjects, their actions/status, and setting.  
- **2** – Covers a majority of important content.  
- **1** – Covers only part of the content.  
- **0** – Irrelevant or extremely vague content.

**Example**:  
3 – *An old man was teasing the dog with a stick on the lawn.*  
2 – *The old man is playing with his dog.*  
1 – *A person and a dog.*  
0 – *I am sorry, I can not a dog.*

---

#### **5. Content Vividness (0–1 point)**  
Evaluate if the description uses specific, sensory, or engaging detail.

- **1** – Includes vivid or descriptive details.  
- **0** – Bland or generic; lacks imagery.

**Example**:  
1 – *The black dog jumps high to catch the trick.*  
0 – *A man is playing with a dog.*

---

#### **6. Sentence Structure (0–1 point)**  
Evaluate sentence complexity and cohesion.

- **1** – Uses compound or complex sentences.  
- **0** – Only uses basic/simple sentence structures.

**Example**:  
1 – *An old man is using a stick to play with the dog, whose face is full of smiles.*  
0 – *An old person is playing with the black dog.*

---

### 🔁 Output Format (Sample)

```
{"grammar": 2, "spelling": 0, "convention": 1, "content_comprehension": 2, "content_vividness": 0, "sentence_structure": 0}
```"""

        passage_json_schema = {
            "format": {
                "type": "json_schema",
                "name": "Passage",
                "schema": {
                    "type": "object",
                    "properties": {
                        "grammar": {"type": "integer"},
                        "spelling": {"type": "integer"},
                        "convention": {"type": "integer"},
                        "content_comprehension": {"type": "integer"},
                        "content_vividness": {"type": "integer"},
                        "sentence_structure": {"type": "integer"},
                    },
                    "required": [
                        "grammar",
                        "spelling",
                        "convention",
                        "content_comprehension",
                        "content_vividness",
                        "sentence_structure"
                    ],
                    "additionalProperties": False
                    },
                    "strict": True,
                }
        }
        if self.first_res_id is None:
            user_inputs=[
                {
                    "role": "user",
                    "content": [
                        { "type": "input_text", "text": sentence},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    ]
                }
            ]
        else:
            user_inputs=[
                {
                    "role": "user",
                    "content": [
                        { "type": "input_text", "text": sentence},
                    ]
                }
            ]
        
        try:
            response = self.client.responses.create(
                model=self.model_name,
                instructions=instructions,
                input=user_inputs,
                temperature=0.1,
                text=passage_json_schema,
                previous_response_id=self.first_res_id
            )

            return json.loads(response.output_text)
        except Exception as e:
            print(f"Error: {e}")
            print(f"Messages: {self.messages}")
            print(f"Response: {response}")
            return {}
    
    def image_similarity(self, image1_base64, image2_base64):
        try:
            user_inputs=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image1_base64}"
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image2_base64}"
                        }
                    ]
                }
            ]
            response = self.client.responses.create(
                model=self.model_name,
                instructions="Compare two input images and calculate a similarity score between 0 and 1, where 1 means identical and 0 means completely different. Base the similarity on visual features such as shapes, colors, and structure. Return only the similarity score as a float.",
                input=user_inputs,
                temperature=0,
            )
                
            similarity_score = float(response.output_text)

            return similarity_score
        
        except Exception as e:
            print(f"Error: {e}")
            return None
        
    def kill(self):
        while self.prev_res_ids:
            prev_res_id = self.prev_res_ids.pop()
            
            self.client.responses.delete(prev_res_id)
            
        self.client=None

        self.first_res_id=None
        self.prev_res_id=None
        self.messages=[]
        gc.collect()
        return True
        
            
        