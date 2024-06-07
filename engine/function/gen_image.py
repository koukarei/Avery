from openai import OpenAI
import urllib.request 

def save_image(url, filename):
    urllib.request.urlretrieve(url, filename)

def gen_image(sentence,size="1024x1024",quality="standard",n=1):
    client = OpenAI()

    response = client.images.generate(
    model="dall-e-3",
    prompt=sentence,
    size=size,
    quality=quality,
    n=n,
    )
    
    return response.data[0].url