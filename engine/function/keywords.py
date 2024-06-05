import base64
import requests
import os
import re

# Function to encode the image
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')
  
def get_ai_keyword_response(im_location):
  # Getting the base64 string
  base64_image = encode_image(im_location)

  headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}"
  }

  payload = {
    "model": "gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "Give keywords to describe the image."
          },
          {
            "type": "image_url",
            "image_url": {
              "url": f"data:image/jpeg;base64,{base64_image}"
            }
          }
        ]
      }
    ],
    "max_tokens": 300
  }

  response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

  return response.json()["choices"][0]["message"]["content"]

def get_ai_keywords(im_location):
    response = get_ai_keyword_response(im_location)
    compiler = re.compile(r'\d+. (.+)\n')
    keywords = compiler.findall(response)
    return keywords