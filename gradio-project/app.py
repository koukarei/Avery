from fastapi import FastAPI, Request, Depends, status, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from lti import validate_lti_request

import os
import json
from typing import Annotated
import datetime

from api import models
from api.connection import *

app = FastAPI(
    root_path="/avery",
)

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

MAX_GENERATION = int(os.getenv("MAX_GENERATION", 5))

@app.route("/login", methods=["GET", "POST"])
async def login_form(request: Request):
    if request.method == "POST":

        form_data = await request.form()
        
        response = await get_access_token_from_backend(form_data=models.UserLogin(**form_data))
        
        templates.TemplateResponse("login_form.html", {"request": request, "error": response.json()})

        token = models.Token(**json.loads(response.json()))

        request.session["token"] = token.model_dump()
        request.session["username"] = form_data["username"]
        request.session["roles"] = "instructor" if form_data["username"] == "admin" else "student"

        # app.state.token = token.model_dump()
        # app.state.username = form_data["username"]

        return RedirectResponse(url='/avery/', status_code=status.HTTP_303_SEE_OTHER)
        
    return templates.TemplateResponse("login_form.html", {"request": request})

@app.route('/lti/login',methods=["POST"])
async def lti_login(request: Request):
    valid = await validate_lti_request(request)
    if not valid:
        return {'error': 'Invalid LTI request'} 
    
    # Extracting additional fields from the form data
    form_data = await request.form()

    user_id = form_data.get('user_id')
    oauth_consumer_key = form_data.get('oauth_consumer_key')

    if user_id:
        school = "School not provided"
        if oauth_consumer_key == "saikyo_consumer_key":
            school = "saikyo"
        elif oauth_consumer_key == "hikone_consumer_key":
            school = "hikone"
        elif oauth_consumer_key == "lms_consumer_key":
            school = "lms"

        if "instructor" in form_data.get('roles', '').lower():
            role = "instructor"
        else:
            role = "student"

        username = form_data.get('ext_user_username')
        user_login = models.UserLti(
            user_id=form_data.get('user_id'),
            username=username,
            display_name=form_data.get('lis_person_name_full', 'Unknown User'),
            roles=role,
            email=form_data.get('lis_person_contact_email_primary', ''),
            school=school,
        )

        response = await get_access_token_from_backend_lti(user=user_login)
        
        if not hasattr(response, 'status_code'):
            token = response
        elif response.status_code == 400:
            # Create user
            response = await create_user_lti(newuser=user_login)
            token = await get_access_token_from_backend_lti(user=user_login)
        else:
            response.raise_for_status()
        
        request.session["school"] = school
        request.session["token"] = token.model_dump()
        request.session["username"] = username
        request.session["roles"] = role
        return RedirectResponse(url='/avery/', status_code=status.HTTP_303_SEE_OTHER)

    raise HTTPException(status_code=500, detail="Failed to login")

@app.route('/logout')
async def logout(request: Request):

    school = request.session.pop('school', None)

    token = request.session.pop('token', None)

    username = request.session.pop('username', None)

    role = request.session.pop('roles', None)

    if school == "saikyo":
        return RedirectResponse(url='https://sk.let.media.kyoto-u.ac.jp')
    elif school == "hikone":
        return RedirectResponse(url='https://leaf02.uchida.co.jp/moodle/')
    elif school == "lms":
        return RedirectResponse(url='https://lms.let.media.kyoto-u.ac.jp/moodle/')
    else:
        return RedirectResponse(url='/login')

@app.post("/token")
def token(request: Request):
    return request.session["token"]["access_token"]

@app.get("/")
async def redirect_page(request: Request):
    if "token" not in request.session:
        try:
            response = await read_leaderboard(request)
            assert response.status_code == 401
        except:
            return RedirectResponse(url="/avery/logout", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/avery/leaderboards", status_code=status.HTTP_303_SEE_OTHER)
    
@app.get("/retry")
async def retry(request: Request):
    request.app.state.generation=None
    the_round=await read_my_rounds(
        request=request,
        is_completed=False,
        leaderboard_id=request.app.state.selected_leaderboard.id,
    )
    if not the_round:
        return RedirectResponse(url="/avery/leaderboards", status_code=status.HTTP_303_SEE_OTHER)
    request.app.state.round=the_round[0]
    return RedirectResponse(url="/avery/answer", status_code=status.HTTP_303_SEE_OTHER)    

@app.get("/resume_game")
async def resume_game(request: Request):
    leaderboard_id = request.app.state.selected_leaderboard.id
    res = await read_my_rounds(
        request=request,
        is_completed=False,
        leaderboard_id=leaderboard_id,
    )

    if not res:
        return RedirectResponse(url="/avery/leaderboards", status_code=status.HTTP_303_SEE_OTHER)
    last_round = res[0]
    request.app.state.round = last_round

    if not last_round.last_generation_id:
        request.app.state.generated_time = 0
        return RedirectResponse(url="/avery/answer", status_code=status.HTTP_303_SEE_OTHER)

    last_gen = await get_generation(
        generation_id=last_round.last_generation_id,
        request=request,
    )
    if last_gen:
        request.app.state.generation=last_gen
        if last_gen.is_completed:
            request.app.state.generated_time = len(last_round.generations)
            if request.app.state.generated_time > (MAX_GENERATION-1):
                output = await end_round(
                    round_id=last_round.id,
                    request=request,
                )
                if not output:
                    raise HTTPException(status_code=500, detail="Failed to end round")
            return RedirectResponse(url="/avery/result", status_code=status.HTTP_303_SEE_OTHER)
        if last_gen.correct_sentence:
            if last_gen.interpreted_image:
                return RedirectResponse(url="/avery/go_to_result", status_code=status.HTTP_303_SEE_OTHER)
            
            output = await get_interpretation(
                round_id=last_round.id,
                interpretation=models.GenerationCorrectSentence(
                    id=last_gen.id,
                    correct_sentence=last_gen.correct_sentence,
                ),
                request=request,
            )

            if not output:
                raise HTTPException(status_code=500, detail="Failed to get interpretation")
            return RedirectResponse(url="/avery/go_to_result", status_code=status.HTTP_303_SEE_OTHER)
        request.app.state.generation=last_gen
        if len(last_round.generations) > 1:
            request.app.state.generated_time = len(last_round.generations)-1
        else:
            request.app.state.generated_time = 0
    return RedirectResponse(url="/avery/answer", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/new_game")
async def new_game(request: Request):
    res = await end_round(request.app.state.round.id, request)
    if res:
        request.app.state.round = None
        request.app.state.generated_time = 0
        request.app.state.generation = None
        request.app.state.selected_leaderboard = None
        return RedirectResponse(url="/avery/leaderboards", status_code=status.HTTP_303_SEE_OTHER)
    raise HTTPException(status_code=500, detail="Failed to end round")

@app.get("/go_to_answer")
async def redirect_to_answer(request: Request):
    if not hasattr(request.app.state, 'selected_leaderboard'):
        return RedirectResponse(url="/avery/leaderboards", status_code=status.HTTP_303_SEE_OTHER)
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
    return RedirectResponse(url="/avery/answer", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/go_to_result")
async def redirect_to_result(request: Request):
    if (not hasattr(request.app.state, 'generation') or not request.app.state.generation) and request.app.state.generated_time < MAX_GENERATION:
        return RedirectResponse(url="/avery/answer", status_code=status.HTTP_303_SEE_OTHER)
    
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

    if request.app.state.generated_time > (MAX_GENERATION-1):
        output = await end_round(
            round_id=request.app.state.round.id, 
            request=request
        )
        if not output:
            raise HTTPException(status_code=500, detail="Round not ended")
    
    return RedirectResponse(url="/avery/result", status_code=status.HTTP_303_SEE_OTHER)

@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    return RedirectResponse(url="/avery/login", status_code=status.HTTP_303_SEE_OTHER)