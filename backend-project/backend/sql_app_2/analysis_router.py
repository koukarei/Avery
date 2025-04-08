import logging.config
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, responses, Security, status
from sqlalchemy.orm import Session
import time, os, datetime, shutil, tempfile, zipfile, zoneinfo, asyncio
import pandas as pd

from . import crud, schemas
from .database import SessionLocal2, engine2

from .dependencies import sentence, score, dictionary, openai_chatbot, util

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