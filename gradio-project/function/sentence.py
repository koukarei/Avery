from openai import OpenAI
import base64

def encode_image(image):
  return base64.b64encode(image).decode('utf-8')

def generateSentence(image):
  base64_image = encode_image(image)
  client=OpenAI()
  completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
      {"role": "system", "content": "You must descibe the image given by the user."},
      {"role": "user", "content": [
        # {"type": "text", "text": "What’s in this image?"},
        {
          "type": "image_url",
          "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image}",
          },
        },
      ]
      }
    ]
  )

  return completion.choices[0].message

def genSentences(image,amt=3):
    gen_Sentences=[]
    for i in range(amt):
        gen_Sentences.append(generateSentence(image).content)
    return gen_Sentences

def checkSentence(sentence,temp=0.5):
  client=OpenAI()
  completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
      {"role": "system", "content": """
       You are English teacher.
       You are going to correct the sentence given by the user. 
       Your input only needs to be the corrected sentence.
       If the sentence is not English, reply with "Please enter an English sentence."
       If the sentence is not valid, reply with "Please enter a valid English sentence."
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