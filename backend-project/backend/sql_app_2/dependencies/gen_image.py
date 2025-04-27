from openai import OpenAI
import urllib.request 

from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64, os, requests
from util import encode_image

def save_image(url, filename):
    urllib.request.urlretrieve(url, filename)

def gen_image(sentence,size="1024x1024",quality="standard",n=1):
    client = OpenAI()

    while True:
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=sentence,
                size=size,
                quality=quality,
                n=n,
                )
            break
        except Exception as e:
            print(f"Error: {e}")
            continue
    return response.data[0].url


def get_image_gemini(prompt):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp-image-generation",
        contents=prompt,
        config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE']
        )
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image = Image.open(BytesIO((part.inline_data.data)))
            return image

def generate_interpretion(sentence, style="in the style of Japanese Anime", model="dall-e-3"):
    if model == "dall-e-3":
        prompt="""
                I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS:
                Generate a image {style} for the passage below.
                
                passage: {passage}
                """.format(passage=sentence, style=style)
        url = gen_image(prompt)
        b_interpreted_image = BytesIO(requests.get(url).content)
        image = encode_image(image_file=b_interpreted_image)
        return image
    elif model == "gemini":
        prompt="""
                Generate a image {style} for the passage below.
                
                passage: {passage}
                """.format(passage=sentence, style=style)
        pil_interpreted_image = get_image_gemini(prompt)
        buffer = BytesIO()
        pil_interpreted_image.save(buffer, format="PNG")
        image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return image
    return None