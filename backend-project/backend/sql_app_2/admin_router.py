import logging.config
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, responses, Security, status, Request
from sqlalchemy.orm import Session
from tasks import generateDescription2
import pandas as pd

from . import crud, schemas
from .database import SessionLocal2, engine2

from .dependencies import wordcloud, sentence
from collections import Counter

from typing import Tuple, List, Annotated, Optional, Union, Literal
from datetime import timezone, timedelta
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

@router.post("/test_frequency", tags=["Frequency"])
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

@router.get("/generate_descriptions", tags=["Description"])
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
