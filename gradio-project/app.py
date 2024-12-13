from fastapi import FastAPI, Request, Depends, status, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

import os
import json
from typing import Annotated

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


@app.route("/login_html", methods=["GET", "POST"])
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
        return RedirectResponse(url="/login_html", status_code=status.HTTP_303_SEE_OTHER)
    elif not hasattr(request.app.state, "selected_leaderboard") or not hasattr(request.app.state, "generated_time"):
        return RedirectResponse(url="/leaderboards", status_code=status.HTTP_303_SEE_OTHER)
    elif "round_id" not in request.session:
        return RedirectResponse(url="/answer", status_code=status.HTTP_303_SEE_OTHER)
    
