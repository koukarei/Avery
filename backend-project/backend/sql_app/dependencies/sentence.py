from openai import OpenAI
from pydantic import BaseModel
import base64
import io

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

class Description(BaseModel):
   details: list[str]

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
  completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
      {"role": "system", "content": """
       You are English teacher.
       You are going to correct the sentence given by the user. 
       Your input only needs to be the corrected sentence.
       If the sentence is not English, reply with "Please enter an English sentence."
       If the sentence is offensive, reply with "Please avoid offensive language."
       If the sentence is correct, reply with the sentence itself.
"""},
      {"role": "user", "content": f"{sentence}"}
    ],
    temperature=temp

  )
  if completion.choices[0].message:
    return completion.choices[0].message.content
  else:
     raise Exception("Sentence correction failed.")