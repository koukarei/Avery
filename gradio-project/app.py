from fastapi import FastAPI, Request, Depends, status, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

import os
import json
from typing import Annotated
import datetime

from api import models
from api.connection import *

app = FastAPI()

@app.on_event("shutdown")
async def shutdown_client():
    await http_client.aclose()

BACKEND_URL = os.getenv("BACKEND_URL")

origins = [
    BACKEND_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=os.environ.get('SECRET_KEY'))

templates = Jinja2Templates(directory="templates")


@app.route("/login", methods=["GET", "POST"])
async def login_form(request: Request):
    if request.method == "POST":

        form_data = await request.form()
        
        response = await get_access_token_from_backend(form_data=models.UserLogin(**form_data))
        
        templates.TemplateResponse("login_form.html", {"request": request, "error": response.json()})

        token = models.Token(**json.loads(response.json()))

        request.session["token"] = token.model_dump()
        request.session["username"] = form_data["username"]

        # app.state.token = token.model_dump()
        # app.state.username = form_data["username"]

        return RedirectResponse(url='/', status_code=status.HTTP_303_SEE_OTHER)
        
    return templates.TemplateResponse("login_form.html", {"request": request})

@app.post("/token")
def token(request: Request):
    return request.session["token"]["access_token"]

@app.get("/")
async def redirect_page(request: Request):
    if "token" not in request.session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(url="/leaderboards", status_code=status.HTTP_303_SEE_OTHER)
    
@app.get("/retry")
async def retry(request: Request):
    request.app.state.generation=None
    return RedirectResponse(url="/answer", status_code=status.HTTP_303_SEE_OTHER)    

@app.get("/new_game")
async def new_game(request: Request):
    res = await end_round(request.app.state.round.id, request)
    if res:
        request.app.state.round = None
        request.app.state.generated_time = 0
        request.app.state.generation = None
        request.app.state.selected_leaderboard = None
        return RedirectResponse(url="/leaderboards", status_code=status.HTTP_303_SEE_OTHER)
    raise HTTPException(status_code=500, detail="Failed to end round")

@app.get("/go_to_answer")
async def redirect_to_answer(request: Request):
    if not hasattr(request.app.state, 'selected_leaderboard'):
        return RedirectResponse(url="/leaderboards", status_code=status.HTTP_303_SEE_OTHER)
    selected_leaderboard_id = request.app.state.selected_leaderboard.id
    output = await create_round(
        new_round=models.RoundStart(
            leaderboard_id=selected_leaderboard_id,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        ),
        request=request,
    )
    request.app.state.round = output
    request.app.state.generated_time = 0
    return RedirectResponse(url="/answer", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/go_to_result")
async def redirect_to_result(request: Request):
    if (not hasattr(request.app.state, 'generation') or not request.app.state.generation) and request.app.state.generated_time < 3:
        return RedirectResponse(url="/answer", status_code=status.HTTP_303_SEE_OTHER)
    
    output = await complete_generation(
        round_id=request.app.state.round.id,
        generation=models.GenerationCompleteCreate(
            id=request.app.state.generation.id,
            at=datetime.datetime.now(datetime.timezone.utc),
        ),
        request=request,
    )
    if not output:
        raise HTTPException(status_code=500, detail="Generation not completed")

    if request.app.state.generated_time > 2:
        output = await end_round(
            round_id=request.app.state.round.id, 
            request=request
        )
        if not output:
            raise HTTPException(status_code=500, detail="Round not ended")
    
    return RedirectResponse(url="/result", status_code=status.HTTP_303_SEE_OTHER)

@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)