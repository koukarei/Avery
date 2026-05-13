import logging.config
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, responses, Security, status, Request
from sqlalchemy.orm import Session
import pandas as pd
import util

from . import crud, schemas
from .database import SessionLocal2, engine2

from .dependencies import wordcloud, sentence, openai_chatbot
from .dependencies.gen_image import generate_interpretion
from collections import Counter

from tasks import app as celery_app
from tasks import generateDescription2, generate_interpretation2, calculate_score_gpt

from typing import Literal
from contextlib import asynccontextmanager
import logging

# Dependency
def get_db():
    db = SessionLocal2()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(
    prefix="/Admin",
)

@router.post("/test_frequency", tags=["Admin", "Frequency"])
async def test_frequency(
    text: str = Form(...),
    lang: Literal['en', 'ja'] = Form('en'),
    db: Session = Depends(get_db),
):
    """
    Test the frequency analysis of a given text.
    """
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    # translate text if necessary
    translated_text = wordcloud.translate_text(text, target_lang=lang)
    
    # Calculate frequency
    frequency = wordcloud.cal_frequency(translated_text)
    
    return {
        "target_lang": lang,
        "original_text": text,
        "translated_text": translated_text,
        "frequency": frequency
    }

@router.get("/generate_descriptions", tags=["Admin", "Description"])
async def generate_descriptions(
    leaderboard_id: int,
    db: Session = Depends(get_db),
):
    db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
    if not db_leaderboard:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    db_original_image = crud.get_original_image(db, image_id=db_leaderboard.original_image_id)

    if db_leaderboard.story_id:
        db_story = crud.get_story(
            db,
            story_id=db_leaderboard.story_id
        )
        story = db_story.content
    else:
        story = ""
    
    t = generateDescription2(
        leaderboard_id=leaderboard_id,
        image=db_original_image.image,
        story=story,
        model_name="gpt-4o-mini"
    )
    return responses.JSONResponse(content={"result": t})

@router.post("/generate_interpretation", tags=["Admin", "Interpretation"])
async def test_generate_interpretation(
    sentence: str = Form(...),
    style: str = Form("in the style of Japanese Anime"),
    model: Literal['gemini', 'gpt-5','dall-e-3','gpt-image-1.5', 'gpt-image-2'] = Form('gemini'),
)->responses.Response:
    if not sentence:
        raise HTTPException(status_code=400, detail="Sentence is required")
    
    interpretation = generate_interpretion(
        sentence=sentence,
        style=style,
        model=model
    )
    
    if interpretation is None:
        raise HTTPException(status_code=500, detail="Failed to generate interpretation")
    
    imgdata=util.decode_image(interpretation)

    # Convert the image to bytes
    return responses.Response(
        content=imgdata,
        media_type="image/png"  # Adjust this based on your image type (jpeg, png, etc.)
    )

@router.post("/generate_evaluation", tags=["Admin", "Evaluation"])
async def test_generate_evaluation(
    sentence: str = Form(...),
    leaderboard_id: int = Form(...),
    db: Session = Depends(get_db)
):
    cb = openai_chatbot.Hint_Chatbot(
        model_name="gpt-4o-mini",
    )
    db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
    if not db_leaderboard:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    db_original_image = crud.get_original_image(db, image_id=db_leaderboard.original_image_id)

    evaluation = cb.get_short_result(
        sentence=sentence,
        correct_sentence=sentence,
        base64_image=db_original_image.image,
        grammar_errors="",
        spelling_errors="",
        descriptions=[]
    )

    if evaluation:
        evaluation_message = """{feedback}""". \
        format(
            feedback=evaluation['feedback']
        )
    return responses.JSONResponse(content={"evaluation": evaluation_message})

@router.get("/writing_traces/{generation_id}", tags=["Admin", "Writing Trace"], response_model=list[schemas.WritingTrace])
async def get_writing_traces(
    generation_id: int,
    db: Session = Depends(get_db)
):
    traces = crud.get_writing_traces(db, generation_id=generation_id)
    return traces