import json
from openai import OpenAI
from dotenv import load_dotenv

# .envファイルの内容を読み込見込む
load_dotenv()

client = OpenAI()

def predict_cefr_en_level(text,temp=0.2):
    # Few-shot examples to teach the model
    system_prompt = """
Here are some examples of texts categorized by their CEFR levels:

A1: "I like apples. I have a cat. My name is John."
A1: "This is a book. It is red. I read it every day."
A1: "She is my sister. Her name is Anna. She is five years old."

A2: "My brother lives in London. We visit him every summer. He works in a bank."
A2: "I usually have cereal for breakfast. Sometimes, I eat toast with butter."
A2: "We went to the park yesterday. It was sunny, and we had a picnic."

B1: "Last year, we went to Spain for vacation. We saw many beautiful places and enjoyed the local cuisine."
B1: "I enjoy reading books in my free time. My favorite genre is mystery."
B1: "She is studying hard because she wants to pass her exams and get a good job."

B2: "The conference on climate change was enlightening. Various experts discussed the impacts of global warming and proposed solutions."
B2: "I have been working on this project for three months, and we have made significant progress."
B2: "She has a diverse range of interests, including art, music, and technology."

C1: "The economic disparity in the region can be attributed to several factors, including historical colonization and modern-day policies."
C1: "His approach to problem-solving is both innovative and effective, often yielding impressive results."
C1: "The novel explores complex themes of identity, morality, and human nature, challenging readers to reflect on their own beliefs."

C2: "The existential philosophies of Sartre and Nietzsche delve into the intricacies of human freedom and the burden of choice."
C2: "Her research provides a comprehensive analysis of the socio-political implications of climate change, highlighting the need for urgent action."
C2: "The symphony's intricate composition and nuanced performances create a profound auditory experience, transcending traditional musical boundaries."

You are going to categorise user's text according to the CEFR levels.
Your answer only needs to be the CEFR level (A1, A2, B1, B2, C1, C2).
"""

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{text}"}
            ],
            temperature=temp

        )
        
        # Check if 'completion' is a dictionary and has a 'choices' key
        if completion.choices[0].message:
            level = completion.choices[0].message.content
        else:
            level = "Unable to determine CEFR level"
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        level = "Error in CEFR level prediction"

    return level