from openai import OpenAI
import urllib.request 

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

def generate_interpretion(sentence):
    prompt="""
            I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS:
            Generate a image in the style of Japanese Anime for the passage below.
            Only show picture.
            passage: {passage}
            """.format(passage=sentence)
    url = gen_image(prompt)
    return url

