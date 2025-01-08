import os
import httpx, threading
import gradio as gr
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, Request, Depends, status, HTTPException
from typing import Annotated, Optional
from PIL import Image as PILImage
import io, datetime

from api import models

BACKEND_URL = os.getenv("BACKEND_URL")

http_client = httpx.AsyncClient()

class BearerAuth(httpx.Auth):
    requires_request_body = True

    def __init__(self, access_token, refresh_token, refresh_url):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.refresh_url = refresh_url
        self._sync_lock = threading.RLock()

    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.access_token}"
        response = yield request
        if response.status_code == 401:
            
            refresh_response = self.build_refresh_request()
            if not hasattr(refresh_response, "status_code"):
                raise HTTPException(status_code=302, detail="Redirect to login page", headers={"Location": "/avery/login"})
            elif refresh_response.status_code != 200:
                raise HTTPException(status_code=302, detail="Redirect to login page", headers={"Location": "/avery/login"})
            self.update_tokens(refresh_response)

            request.headers["Authorization"] = f"Bearer {self.access_token}"
            yield request

    def build_refresh_request(self):
        with self._sync_lock:
            response = http_client.post(
                self.refresh_url,
                data={"refresh_token": self.refresh_token}
            )
        return response
    
    def update_tokens(self, response):
        data = response.json()
        self.access_token = data["access_token"]

def convert_json(mdl: models.BaseModel):
    json_data = mdl.model_dump()
    if "created_at" in json_data:
        json_data["created_at"] = json_data["created_at"].isoformat()
    if "at" in json_data:
        json_data["at"] = json_data["at"].isoformat()
    return json_data

async def create_user(newuser: models.UserCreate):
    url = f"{BACKEND_URL}users"

    response = await http_client.post(
        url, 
        json=newuser.model_dump(),
        headers={"Content-Type": "application/json"}
    )
    return response

async def create_user_lti(newuser: models.UserLti):
    url = f"{BACKEND_URL}users/lti"

    response = await http_client.post(
        url, 
        json=newuser.model_dump(),
        headers={"Content-Type": "application/json"}
    )
    
    return response

async def get_access_token_from_backend(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}token", 
                data={
                "username": form_data.username,
                "password": form_data.password
                }, 
                follow_redirects=True
            )
            response.raise_for_status()
            token = models.Token(**response.json())  
            return token
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code)
    
async def get_access_token_from_backend_lti(
        user: models.UserLti,
):
    try:
        response = await http_client.post(
            f"{BACKEND_URL}lti/token", 
            json=user.model_dump(), 
            headers={"Content-Type": "application/json"},
            follow_redirects=True
        )
        if response.status_code == 400:
            return response
        response.raise_for_status()
        token = models.Token(**response.json())  
        return token
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code)

def get_auth(request: Request):
    bearer = BearerAuth(
        access_token=request.session["token"]["access_token"],
        refresh_token=request.session["token"]["refresh_token"],
        refresh_url=f"{BACKEND_URL}refresh_token"
    )
    return bearer

async def read_leaderboard(
        request: Request, 
        published_at_start: Optional[datetime.datetime] = None,
        published_at_end: Optional[datetime.datetime] = datetime.datetime.now()
):
    auth = get_auth(request)
    url = f"{BACKEND_URL}leaderboards"
    if published_at_start:
        # convert to utczone
        published_at_start = published_at_start.astimezone(datetime.timezone.utc)
        url += f"?published_at_start={published_at_start.strftime('%d%m%Y')}"

    if published_at_end:
        # convert to utczone
        published_at_end = published_at_end.astimezone(datetime.timezone.utc)
        if published_at_start:
            url += f"&published_at_end={published_at_end.strftime('%d%m%Y')}"
        else:
            url += f"?published_at_end={published_at_end.strftime('%d%m%Y')}"

    try:
        response = await http_client.get(
            url,
            auth=auth,
            follow_redirects=True
        )
        response.raise_for_status()
        output = [models.Leaderboard(**leaderboard) for leaderboard in response.json()]
        return output
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

async def delete_leaderboard(leaderboard_id: int, request: Request):
    response = await http_client.delete(
        f"{BACKEND_URL}leaderboards/{leaderboard_id}",
        auth=get_auth(request),
    )
    response.raise_for_status()
    output = models.IdOnly(**response.json())
    return output

async def get_original_images(leaderboard_id: int, request: Request):
    response = await http_client.get(
        f"{BACKEND_URL}original_image/{leaderboard_id}",
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    image = PILImage.open(io.BytesIO(response.content))
    return image

async def create_round(new_round: models.RoundStart, request: Request, ):
    json_data = convert_json(new_round)
    response = await http_client.post(
        f"{BACKEND_URL}round/", 
        json=json_data,
        headers={
            "Content-Type": "application/json",
        },
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    output = models.RoundStartOut(**response.json())
    return output
    
async def read_my_rounds(request: Request, is_completed: bool = False, leaderboard_id: int = None):
    if leaderboard_id is None:
        url = f"{BACKEND_URL}my_rounds/?is_completed={is_completed}"
    else:
        url = f"{BACKEND_URL}my_rounds/?is_completed={is_completed}&leaderboard_id={leaderboard_id}"

    response = await http_client.get(
        url,
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    output = [models.Round(**round) for round in response.json()]
    return output

async def send_message(round_id: int, new_message:models.MessageSend, request: Request, ):
    json_data = convert_json(new_message)
    response = await http_client.put(
        f"{BACKEND_URL}round/{round_id}/chat",
        json=json_data,
        headers={"Content-Type": "application/json",
        },
        auth=get_auth(request),
        timeout=20
    )
    if response.status_code != 200:
        return None
    output = models.Chat(**response.json())
    return output

async def get_chat(round_id: int, request: Request, ):
    response = await http_client.get(
        f"{BACKEND_URL}chat/{round_id}",
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    output = models.Chat(**response.json())
    return output

async def create_generation(new_generation: models.GenerationStart, request: Request, ):
    json_data = convert_json(new_generation)
    response = await http_client.put(
        f"{BACKEND_URL}round/{new_generation.round_id}",
        json=json_data,
        headers={"Content-Type": "application/json",
        },
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    output = models.GenerationCorrectSentence(**response.json())
    return output

async def get_interpretation(round_id: int, interpretation: models.GenerationCorrectSentence, request: Request, ):
    # get interpretation
    response = await http_client.put(
        f"{BACKEND_URL}round/{round_id}/interpretation",
        json=interpretation.model_dump(),
        headers={"Content-Type": "application/json",
        },
        auth=get_auth(request),
        timeout=90
    )
    if response.status_code != 200:
        return None
    output = models.GenerationInterpretation(**response.json())
    return output

async def get_interpreted_image(generation_id: int, request: Request, ):
    response = await http_client.get(
        f"{BACKEND_URL}interpreted_image/{generation_id}",
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    image = PILImage.open(io.BytesIO(response.content))
    return image

async def complete_generation(round_id: int, generation: models.GenerationCompleteCreate, request: Request, ):
    json_data = convert_json(generation)
    response = await http_client.put(
        f"{BACKEND_URL}round/{round_id}/complete",
        json=json_data,
        headers={"Content-Type": "application/json",
        },
        auth=get_auth(request),
        timeout=120
    )
    if response.status_code != 200:
        return None
    output = models.GenerationComplete(**response.json())
    return output

async def end_round(round_id: int, request: Request, ):
    # Test complete round
    response = await http_client.post(
        f"{BACKEND_URL}round/{round_id}/end",
        headers={"Content-Type": "application/json",
        },
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    output = models.Round(**response.json())
    return output

async def get_image_similarity(generation_id: int, request: Request, ):
    response = await http_client.get(
        f"{BACKEND_URL}image_similarity/{generation_id}",
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    output = models.ImageSimilarity(**response.json())
    return output

async def get_rounds(leaderboard_id: int, request: Request):
    response = await http_client.get(
        f"{BACKEND_URL}leaderboards/{leaderboard_id}/rounds",
        auth=get_auth(request),
        follow_redirects=True
    )
    if response.status_code != 200:
        return None
    output = [models.Round(**round) for round in response.json()]
    return output

async def get_generation(generation_id: int, request: Request):
    response = await http_client.get(
        f"{BACKEND_URL}generation/{generation_id}",
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    output = models.GenerationOut(**response.json())
    return output

async def get_generation_score(generation_id: int, request: Request):
    response = await http_client.get(
        f"{BACKEND_URL}generation/{generation_id}/score",
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    return response.json()

async def check_playable(
        leaderboard_id: int, 
        request: Request,
):
    response = await http_client.get(
        f"{BACKEND_URL}leaderboards/{leaderboard_id}/playable",
        auth=get_auth(request),
    )
    
    if response.status_code != 200:
        return None
    return response.json()['is_playable']

async def get_users(request: Request):
    response = await http_client.get(
        f"{BACKEND_URL}users",
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    output = [models.User(**user) for user in response.json()]
    return output

async def get_generations(
    request: Request,
    leaderboard_id: Optional[int] = None, 
    player_id: Optional[int] = None, 
    school_name: Optional[str] = None
):
    if school_name:
        if leaderboard_id and player_id:
            url = f"{BACKEND_URL}generations/?leaderboard_id={leaderboard_id}&player_id={player_id}&school_name={school_name}"
        elif leaderboard_id:
            url = f"{BACKEND_URL}generations/?leaderboard_id={leaderboard_id}&school_name={school_name}"
        elif player_id:
            url = f"{BACKEND_URL}generations/?player_id={player_id}&school_name={school_name}"
        else:
            url = f"{BACKEND_URL}generations/?school_name={school_name}"
    else:
        if leaderboard_id and player_id:
            url = f"{BACKEND_URL}generations/?leaderboard_id={leaderboard_id}&player_id={player_id}"
        elif leaderboard_id:
            url = f"{BACKEND_URL}generations/?leaderboard_id={leaderboard_id}"
        elif player_id:
            url = f"{BACKEND_URL}generations/?player_id={player_id}"
        else:
            url = f"{BACKEND_URL}generations"

    response = await http_client.get(
        url,
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    output = [models.GenerationRound(
        generation=generation[0],
        round=generation[1]
    ) for generation in response.json()]
    return output