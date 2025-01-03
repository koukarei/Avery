from openai import OpenAI
from pydantic import BaseModel

class Description(BaseModel):
   details: list[str]

class Passage(BaseModel):
   status: int
   corrected_passage: str


def generateSentence(image,story, model_name="gpt-4o-2024-08-06"):
  
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
       image="data:image/jpeg;base64,{}".format(image)
    for i in range(amt):
        gen_Sentences=generateSentence(image,story)
    return gen_Sentences

def checkSentence(passage,temp=1):
  client=OpenAI()
  completion = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
      {"role": "system", "content": """
# Role
Language and content validator

## Action
Analyze a passage to determine:
1. If it's non-English, return status 1.
2. If it's offensive, return status 2.
3. Otherwise, return status 0 and provide a grammatically correct, spell-checked version of the passage.

## Skills
- Language detection
- Content moderation
- Grammar correction
- Spelling correction

## Format
- Output in the form: `{"status": X, "message": "Corrected passage or reason for status 1/2"}`
- Ensure output follows a JSON-like structure for easy integration.

## Constraints
- Must detect non-English text accurately.
- Must detect offensive or inappropriate content with high precision.
- Correct spelling and grammar only for English text.
- Message should not exceed 1000 characters.
- Ensure the corrected passage is American English.

## Example
Input: "This is an exmple of bad grammar!"
Output: `{"status": 0, "message": "This is an example of bad grammar!"}`

Input: "Esto es un ejemplo."
Output: `{"status": 1, "message": "ブー！英語で答えてください。"}`

Input: "Fuck You!"
Output: `{"status": 2, "message": "ブー！不適切な言葉が含まれています。"}`
"""},
      {"role": "user", "content": f"{passage}"}
    ],
    temperature=temp,
    response_format=Passage,

  )
  output = completion.choices[0].message.parsed
  if output:
    return output.status, output.corrected_passage
  else:
     raise Exception("Sentence correction failed.")