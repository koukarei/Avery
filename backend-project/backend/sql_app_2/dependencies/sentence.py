from openai import OpenAI
from pydantic import BaseModel
import json

class Description(BaseModel):
   details: list[str]

class SpellingMistake(BaseModel):
   word: str
   correction: str

class GrammarMistake(BaseModel):
   extracted_text: str
   explanation: str
   correction: str

class Passage(BaseModel):
   status: int
   corrected_passage: str
   spelling_mistakes: list[SpellingMistake]
   grammar_mistakes: list[GrammarMistake]


def generateSentence(base64_image,story: str=None, model_name="gpt-4o"):
  
  client=OpenAI()
  system_prompt = """
# Role
Image Describer

## Action
Provide a detailed, line-by-line description of the image, incorporating relevant elements of a story provided by the user.

## Skills
- Strong observational skills
- Ability to create vivid and accurate descriptions
- Proficient in integrating narrative elements into visual descriptions
- Creative storytelling abilities

## Format
1. Break the description into detailed, numbered lines.
2. Use clear and vivid language for each line.
3. Tie in the user-provided story where relevant to enhance coherence.

## Constrains
- Maintain clarity and conciseness in each line.
- Avoid overloading the description with unnecessary details.

## Example
1. A golden sunset casts a warm glow over a tranquil beach.
2. The story's main character stands at the shore, gazing at the horizon with a hopeful expression.
3. Seagulls glide across the sky, echoing the calm yet melancholic mood of the story.
4. Gentle waves lap at the sand, their rhythm mirroring the character's deep breaths.
      """
  
  messages = []
  if story:
    messages.append(
      {"role": "user", "content": [
        {"type": "input_text", "text": story},
        {
          "type": "input_image",
          "image_url": f"data:image/jpeg;base64,{base64_image}"
        },
      ]
      }
    )
  else:
      {"role": "user", "content": [
        {
          "type": "input_image",
          "image_url": f"data:image/jpeg;base64,{base64_image}"
        },
      ]
      }
      
  response = client.responses.create(
    model=model_name,
    instructions=system_prompt,
    input=messages,
    temperature=0.5,
    text={
       "format": "json_schema",
       "name": "description",
       "schema": {
          "type": "object",
          "properties": {
            "details": {
              "type": "array",
              "items": {
                "type": "string"
              }
            }
          },
          "required": ["details"]
        },
        "strict": True,
       }
  )

  description = json.loads(response.output_text)
  
  return response.id, description['details']

def genSentences(image,story,amt=3):
    
    if "http" not in image:
       image="data:image/jpeg;base64,{}".format(image)
    for i in range(amt):
        response_id, gen_Sentences=generateSentence(image,story)
    return response_id, gen_Sentences

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
Output: `{"status": 0, "message": "This is an example of bad grammar!", "spelling_mistakes": [{"word":"exmple","correction":"example"}], "grammar_mistakes": []}`

Input: "Esto es un ejemplo."
Output: `{"status": 1, "message": "ブー！英語で答えてください。", "spelling_mistakes": [], "grammar_mistakes": []}`

Input: "I love neko."
Output: `{"status": 1, "message": "ブー！英語で答えてください。", "spelling_mistakes": [], "grammar_mistakes": []}`

Input: "Fuck You!"
Output: `{"status": 2, "message": "ブー！不適切な言葉が含まれています。", "spelling_mistakes": [], "grammar_mistakes": []}`
       
Input: "I am walk in a dessert"
Output: `{"status": 0, "message": "I walk in a desert", "spelling_mistakes": [{"word":"dessert","correction":"desert"}], "grammar_mistakes": [{"extracted_text": "I am walk","explanation":"一般動詞の原形・現在形・過去形は単独で述語動詞になるので、be動詞と一緒に使うことはできません。","correction":"I walk"}]}`
"""},
      {"role": "user", "content": f"{passage}"}
    ],
    temperature=temp,
    response_format=Passage,

  )
  output = completion.choices[0].message.parsed
  if output:
    return output.status, output.corrected_passage, output.spelling_mistakes, output.grammar_mistakes
  else:
     raise Exception("Sentence correction failed.")