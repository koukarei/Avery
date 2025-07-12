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
    program: Literal["none", "inlab_test","haga_sensei_test","student_january_experiment","student_1_sem_awe","student_1_sem_img"],
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

@router.get("/leaderboards/{leaderboard_id}/{program_name}", tags=["analysis"], response_model=schemas.LeaderboardAnalysis)
async def read_word_cloud(
    leaderboard_id: int,
    program_name: Literal["none", "inlab_test","haga_sensei_test","student_january_experiment","student_1_sem_awe","student_1_sem_img"],
    cloud_type: Literal['mistake', 'writing', 'user_chat', 'assistant_chat'] = 'mistake',
    lang: Literal['ja', 'en'] = 'en',
    db: Session = Depends(get_db)
):
    """
    Get the leaderboard analysis for a specific program.
    """
    db_program = crud.get_program_by_name(db, program_name)
    
    # Check if word cloud exists
    if not db_program:
        raise HTTPException(status_code=404, detail="Program not found")
    db_leaderboard_analysis = crud.read_leaderboard_analysis(
        db=db,
        leaderboard_id=leaderboard_id,
        program_id=db_program.id,
    )
    if not db_leaderboard_analysis:
        db_leaderboard_analysis = crud.create_leaderboard_analysis(
            db=db,
            leaderboard_id=leaderboard_id,
            program_id=db_program.id,
        )

    # Check if generations exist for the leaderboard and program
    # If not, no need to create a new word cloud
    db_generations = crud.get_generations(
        db=db,
        program_id=db_program.id,
        leaderboard_id=leaderboard_id,
        limit=10000,
    )

    if not db_generations and '_chat' not in cloud_type:
        raise HTTPException(status_code=404, detail="No generations found for the leaderboard and program")

    # Check if rounds exist for the leaderboard and program
    # If not, no need to create a new word cloud
    db_rounds = crud.get_rounds(
        db=db,
        leaderboard_id=leaderboard_id,
        program_id=db_program.id,
        limit=10000,
    )
    if not db_rounds:
        raise HTTPException(status_code=404, detail="No rounds found for the leaderboard and program")

    db_leaderboard_wordcloud = crud.read_leaderboard_analysis_word_cloud(
        db=db,
        leaderboard_analysis_id=db_leaderboard_analysis.id,
        cloud_type=cloud_type,
        lang=lang,
    )

    if db_leaderboard_wordcloud:
        # Calculate frequency of each word
        db_word_cloud = crud.read_word_cloud(
            db=db,
            id=db_leaderboard_wordcloud[0].word_cloud_id,
        )

        # Check if new generation before updating word cloud

    else:
        # Create the word cloud
        db_word_cloud = crud.create_word_cloud(
            db=db,
            cloud_type=cloud_type,
            word_cloud=schemas.WordCloudCreate(
                last_updated=datetime.datetime.now(
                    tz=zoneinfo.ZoneInfo("Asia/Tokyo")
            ),
            latest_generation_id=db_generations[-1].id if db_generations else None,
            )
        )

        db_leaderboard_wordcloud = crud.create_leaderboard_analysis_word_cloud(
            db=db,
            leaderboard_analysis_word_cloud=schemas.LeaderboardAnalysis_WordCloudCreate(
                leaderboard_analysis_id=db_leaderboard_analysis.id,
                word_cloud_id=db_word_cloud.id,
                type=cloud_type,
                lang=lang,
            )
        )