import base64
import requests
import os
import re

from PIL import Image
from io import BytesIO

def compress_and_convert_image(img, output_format='JPEG', quality=85):
  # Convert the image to RGB if it has an alpha channel
  if img.mode in ('RGBA', 'LA'):
      img = img.convert('RGB')
  img.resize((1024,1024))
  buffer = BytesIO()

  # Compress and save the image
  img.save(buffer, format=output_format, quality=quality)
  
  byte_data = buffer.getvalue()
  buffer.close()
  return byte_data

# Function to encode the image
def encode_image(image_path):
  if type(image_path)==str:
    with Image.open(image_path) as image_file:
      if isinstance(image_file,Image.Image):
        image_file=compress_and_convert_image(image_file)
        return base64.b64encode(image_file).decode('utf-8')
      image_file=compress_and_convert_image(image_file.read())
      return base64.b64encode(image_file).decode('utf-8')
  image_file=Image.fromarray(image_path)
  image_file=compress_and_convert_image(image_file)
  return base64.b64encode(image_file).decode('utf-8')

def get_ai_keyword_response(im_location,current_keywords=[]):
  # Getting the base64 string
  img = encode_image(im_location)
  
  if current_keywords:
    user_prompt = " Exclude keywords listed and their synonym: \n" + '\n'.join(current_keywords) + "."
  else:
    user_prompt = ""

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
            "text": f"Give keywords to describe the image.{user_prompt} Give your answer in the following format: keyword1, keyword2, keyword3."
          },
          {
            "type": "image_url",
            "image_url": {
              "url": f"data:image/jpeg;base64,{img}"
            }
          }
        ]
      }
    ],
    "max_tokens": 300
  }

  response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

  #print(response.json())
  return response.json()["choices"][0]["message"]["content"]

def get_ai_keywords(im_location,current_keywords=[]):
    response = get_ai_keyword_response(im_location,current_keywords=current_keywords)
    #compiler = re.compile(r'\d+. (.+)\n')
    keywords = response.split(", ")
    return keywords