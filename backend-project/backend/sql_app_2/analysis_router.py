import logging.config
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, responses, Security, status
from sqlalchemy.orm import Session
import time, os, datetime, shutil, tempfile, zipfile, zoneinfo, asyncio
import pandas as pd

from . import crud, schemas
from .database import SessionLocal2, engine2

from .dependencies import wordcloud

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
    prefix="/analysis",
)

@router.post("/test_frequency", tags=["analysis"])
async def test_frequency(
    text: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Test the frequency analysis of a given text.
    """
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    # translate text if necessary
    translated_text = wordcloud.translate_text(text, target_lang='en')
    
    # Calculate frequency
    frequency = wordcloud.cal_frequency(translated_text)
    
    return {
        "target_lang": 'en',
        "original_text": text,
        "translated_text": translated_text,
        "frequency": frequency
    }

@router.get("/generations", tags=["analysis"], response_model=list[Tuple[schemas.GenerationAnalysis, schemas.RoundAnalysis]])
async def read_generations(
    program: Literal["none", "inlab_test","haga_sensei_test","student_january_experiment"],
    db: Session = Depends(get_db)
):
    if program == "none":
        generations = crud.get_generations(
            db,
            limit=10000,
        )
        return generations
    program = crud.get_program_by_name(db, program)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    generations = crud.get_generations(
        db, 
        program_id=program.id,
        limit=10000,
    )

    return generations