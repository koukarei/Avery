from openai import OpenAI
from pydantic import BaseModel
import base64
import io
from typing import Optional

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

class Description(BaseModel):
   details: list[str]

class Passage(BaseModel):
   status: int
   corrected_passage: Optional[str]


def generateSentence(image,story, model_name="gpt-4o-2024-08-06"):
  #base64_image = encode_image(image)
  client=OpenAI()
  completion = client.beta.chat.completions.parse(
    model=model_name,
    messages=[
      {"role": "system", "content": """
        Describe the image in details, line by line.
        You can make reference to the story given by the user.
       """},
      {"role": "user", "content": [
        {"type": "text", "text": story},
        {
          "type": "image_url",
          "image_url": {
            "url": image,
          },
        },
      ]
      }
    ],
    response_format=Description,
  )

  description = completion.choices[0].message.parsed
  
  return description.details

def genSentences(image,story,amt=3):
    
    if "http" not in image:
       image="data:image/jpeg;base64,{}".format(encode_image(image))
    for i in range(amt):
        gen_Sentences=generateSentence(image,story)
    return gen_Sentences

def checkSentence(sentence,temp=0.3):
  client=OpenAI()
  completion = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
      {"role": "system", "content": """
       Transform the passage into a grammatically correct passage without any spelling mistake.
       If the passage is not English, respond with status 1."
       If the passage is offensive, respond with status 2."
       Otherwise, respond with status 0 and the corrected passage."
"""},
      {"role": "user", "content": f"{sentence}"}
    ],
    temperature=temp,
    response_format=Passage,

  )
  output = completion.choices[0].message.parsed
  if output:
    return output.status, output.corrected_passage
  else:
     raise Exception("Sentence correction failed.")