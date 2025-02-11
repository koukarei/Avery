import logging.config
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, responses, Security, status
from sqlalchemy.orm import Session
import time, os, datetime, shutil, tempfile, zipfile, zoneinfo, asyncio
import pandas as pd

from . import crud, schemas
from .database import SessionLocal, engine

from .dependencies import sentence, score, dictionary, openai_chatbot, util

from typing import Tuple, List, Annotated, Optional, Union, Literal
from datetime import timezone, timedelta
from contextlib import asynccontextmanager
import logging

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(
    prefix="/analysis",
)

@router.get("/generations", tags=["analysis"], response_model=list[Tuple[schemas.GenerationOut, schemas.RoundOut]])
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
    generations = crud.get_generations(
        db, 
        program_id=program.id,
        limit=10000,
    )

    return generations