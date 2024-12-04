from fastapi import FastAPI, File, UploadFile, Form
from contextlib import asynccontextmanager
from typing import Annotated
import torch
import uuid, os, PIL

device = None
blip2_model = None
vis_processors = None
text_processors = None

from lavis.models import load_model_and_preprocess

@asynccontextmanager
async def load_blip2_model(app: FastAPI):
    try:
        global blip2_model, vis_processors, text_processors, device
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        blip2_model, vis_processors, text_processors = load_model_and_preprocess(
            "blip2_image_text_matching", "pretrain", device=device, is_eval=True
        )
        yield
    except Exception as e:
        raise ValueError(f"Error loading BLIP2 model: {e}")
    finally:
        blip2_model = None
        vis_processors = None
        text_processors = None
        device = None

app = FastAPI(
    title="BLIP2 Content Score API",
    lifespan=load_blip2_model,
)

@app.get("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.post('/content_score')
async def calculate_content_score(
    image: Annotated[UploadFile, File()],
    sentence: Annotated[str, Form()],
):
    handle_id = uuid.uuid4().hex
    file=image.file

    os.makedirs("media", exist_ok=True)
    if not os.path.isdir("media"):
        raise ValueError("Media directory not found")

    while os.path.isfile(f"media/{handle_id}.jpg"):
        handle_id = uuid.uuid4().hex

    image_path = f"media/{handle_id}.jpg"

    if file:
        file.save(image_path)
        assert os.path.isfile(image_path)
    else:
        raise ValueError("Image not found")

    raw_image = PIL.Image.open(image_path).convert("RGB")

    if blip2_model is None:
        load_blip2_model()

    img = vis_processors["eval"](raw_image).unsqueeze(0).to(device)
    txt = text_processors["eval"](sentence)

    itm_output = blip2_model({"image": img, "text_input": txt}, match_head="itm")
    itm_scores = torch.nn.functional.softmax(itm_output, dim=1)
    content_score = await itm_scores[:, 1].item()*100
    # print(f'The image and text are matched with a probability of {itm_scores[:, 1].item():.3%}')

    # itc_score = model({"image": img, "text_input": txt}, match_head='itc')
    # print('The image feature and text feature has a cosine similarity of %.4f'%itc_score)
    
    if os.path.isfile(image_path):
        os.remove(image_path)
    
    return {'content_score':int(round(content_score))}