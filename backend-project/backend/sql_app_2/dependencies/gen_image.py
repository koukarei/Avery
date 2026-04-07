from openai import OpenAI
import urllib.request 

from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64, os, requests, time
from util import encode_image, logger_image
from typing import Literal

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

def gen_image_gpt_image_1_5(prompt):
    client = OpenAI()
    while True:
        try:
            result = client.images.generate(
                model="gpt-image-1.5",
                prompt=prompt
            )

            if result and result.data and result.data[0].b64_json:
                break
        except Exception as e:
            print(f"Error: {e}")
            continue
    return result.data[0].b64_json

def gen_image_gpt_5(prompt):
    client = OpenAI()
    while True:
        try:
            response = client.responses.create(
                model="gpt-5",
                input=prompt,
                tools=[{"type": "image_generation"}],
            )

            image_data = [
                output.result
                for output in response.output
                if output.type == "image_generation_call"
            ]

            if image_data:
                break
        except Exception as e:
            print(f"Error: {e}")
            continue
    return image_data[0]
       
def gen_image_gemini(prompt):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    while True:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt],
                config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
                )
            )
            logger_image.info(f"Response: {prompt}")
            for part in response.parts:
                if part.text is not None:
                    logger_image.info(f"Text part: {part.text}")
                elif part.inline_data is not None:
                    logger_image.info(f"Image part: {part.inline_data.mime_type}")
                    image = Image.open(BytesIO((part.inline_data.data)))
                    return image
        # Catch 429 RESOURCE_EXHAUSTED error and retry
        except genai.errors.APIError as e:
            logger_image.error(f"Resource exhausted: {e}")
            details = e.response.json().get('error', {}).get('details', [])
            for detail in details:
                if detail.get('@type') == 'type.googleapis.com/google.rpc.RetryInfo':
                    retry_delay = detail.get('retryDelay')
                    time.sleep(int(retry_delay.split('s')[0]))

def generate_interpretion(
    sentence, 
    style="in the style of Japanese Anime", 
    model="gpt-image-1.5"
) -> str | None:
    
    # This function generates an image based on the input sentence and style using the specified model.
    # model: "dall-e-3", "gpt-image-1.5","gpt-5", "gemini"

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
    elif model == "gpt-image-1.5":
        prompt = "Hi, please create an image {style} to show that {passage}".format(passage=sentence, style=style)
        base64_image = gen_image_gpt_image_1_5(prompt)
        return base64_image
    elif model == "gpt-5":
        prompt = "Generate an image {style} to show that {passage}".format(passage=sentence, style=style)
        base64_image = gen_image_gpt_5(prompt)
        return base64_image
    elif model == "gemini":
        prompt="Hi, please create an image {style} to show that {passage}".format(passage=sentence, style=style)
        pil_interpreted_image = gen_image_gemini(prompt)
        buffer = BytesIO()
        pil_interpreted_image.save(buffer, format="PNG")
        image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return image
    return None