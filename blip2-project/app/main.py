from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from contextlib import asynccontextmanager
from typing import Annotated
import torch
import uuid, os, PIL, io, base64


models={}

from lavis.models import load_model_and_preprocess

def load_blip2_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # blip2_model, vis_processors, text_processors = load_model_and_preprocess(
    #     "blip_image_text_matching", "large", device=device, is_eval=True
    # )
    blip2_model, vis_processors, text_processors = load_model_and_preprocess(
        "blip2_image_text_matching", "pretrain", device=device, is_eval=True
    )
    return blip2_model, vis_processors, text_processors, device

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        models['blip2_model'], models['vis_processors'], models['text_processors'], models['device'] = load_blip2_model()
        yield
    except Exception as e:
        raise ValueError(f"Error loading BLIP2 model: {e}")
    finally:
        models.clear()

app = FastAPI(
    title="BLIP2 Content Score API",
    lifespan=lifespan,
    debug=True
)

@app.get("/")
def hello_world():
    return {"message": "Hello World"}

@app.post('/fake_content_score')
async def fake_content_score(
    image: Annotated[UploadFile, File()],
    sentence: Annotated[str, Form()],
):
    return {'content_score': 50}


@app.post('/content_score')
async def calculate_content_score(
    image: Annotated[UploadFile, File()],
    sentence: Annotated[str, Form()],
):
    try:
        raw_image = PIL.Image.open(image.file).convert("RGB")
        if 'blip2_model' not in models or 'vis_processors' not in models or 'text_processors' not in models or 'device' not in models:
            models['blip2_model'], models['vis_processors'], models['text_processors'], models['device'] = load_blip2_model()

        img = models['vis_processors']["eval"](raw_image).unsqueeze(0).to(models['device'])
        txt = models['text_processors']["eval"](sentence)

        itm_output = models['blip2_model']({"image": img, "text_input": txt}, match_head="itm")
        itm_scores = torch.nn.functional.softmax(itm_output, dim=1)
        content_score = itm_scores[:, 1].item()*100

        # print(f'The image and text are matched with a probability of {itm_scores[:, 1].item():.3%}')

        # itc_score = model({"image": img, "text_input": txt}, match_head='itc')
        # print('The image feature and text feature has a cosine similarity of %.4f'%itc_score)
        
        return {'content_score':int(round(content_score))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating content score: {e}")
    
@app.post('/content_score/base64')
async def calculate_content_score_base64(
    image: Annotated[str, Form()],
    sentence: Annotated[str, Form()],
):
    im_btyes = base64.b64decode(image)
    im_file = io.BytesIO(im_btyes)

    try:
        raw_image = PIL.Image.open(im_file).convert("RGB")
        if 'blip2_model' not in models or 'vis_processors' not in models or 'text_processors' not in models or 'device' not in models:
            models['blip2_model'], models['vis_processors'], models['text_processors'], models['device'] = load_blip2_model()

        img = models['vis_processors']["eval"](raw_image).unsqueeze(0).to(models['device'])
        txt = models['text_processors']["eval"](sentence)

        itm_output = models['blip2_model']({"image": img, "text_input": txt}, match_head="itm")
        itm_scores = torch.nn.functional.softmax(itm_output, dim=1)
        content_score = itm_scores[:, 1].item()*100

        # print(f'The image and text are matched with a probability of {itm_scores[:, 1].item():.3%}')

        # itc_score = model({"image": img, "text_input": txt}, match_head='itc')
        # print('The image feature and text feature has a cosine similarity of %.4f'%itc_score)
        
        return {'content_score':int(round(content_score))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating content score: {e}")