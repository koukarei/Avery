import os
import httpx
import gradio as gr
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, Request, Depends, status, HTTPException
from typing import Annotated
from api import models

BACKEND_URL = os.getenv("BACKEND_URL")

http_client = httpx.AsyncClient()

class BearerAuth(httpx.Auth):
    requires_request_body = True

    def __init__(self, access_token, refresh_token, refresh_url):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.refresh_url = refresh_url

    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.access_token}"
        print(f"Request: {request}")
        print(f"Headers: {request.headers}")
        response = yield request
        if response.status_code == 401:

            refresh_response = yield self.build_refresh_request()
            self.update_tokens(refresh_response)

            request.headers["Authorization"] = f"Bearer {self.access_token}"
            yield request

    def build_refresh_request(self):
        response = http_client.post(
            self.refresh_url,
            data={"refresh_token": self.refresh_token}
        )
        return response
    
    def update_tokens(self, response):
        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]

async def create_user(newuser: models.UserCreate):
    url = f"{BACKEND_URL}users"

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
    
def get_auth(request: Request):
    bearer = BearerAuth(
        access_token=request.session["token"]["access_token"],
        refresh_token=request.session["token"]["refresh_token"],
        refresh_url=f"{BACKEND_URL}refresh_token"
    )
    return bearer

async def read_leaderboard(request: Request):
    auth = get_auth(request)
    url = f"{BACKEND_URL}leaderboards"
    try:
        response = await http_client.get(
            url,
            auth=auth,
            follow_redirects=True
        )
        print(f"Response: {response.json()}")
        response.raise_for_status()
        output = models.Leaderboard(**response.json())
        return output
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

async def get_original_images(leaderboard_id: int, request: Request, ):
    response = await http_client.get(
        f"{BACKEND_URL}original_image/{leaderboard_id}",
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    return response

async def create_round(new_round: models.RoundStart, request: Request, ):
    response = await http_client.post(
        f"{BACKEND_URL}round/", 
        json=new_round.model_dump(),
        headers={
            "Content-Type": "application/json",
        },
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    output = models.RoundStartOut(**response.json())
    return output
    
async def read_unfinished_rounds(request: Request):
    response = await http_client.get(
        f"{BACKEND_URL}unfinished_rounds/",
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    output = [models.Round(**round) for round in response.json()]
    return output

async def send_message(round_id: int, new_message:models.MessageSend, request: Request, ):
    response = await http_client.put(
        f"{BACKEND_URL}round/{round_id}/chat",
        json=new_message.model_dump(),
        headers={"Content-Type": "application/json",
        },
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    output = models.Chat(**response.json())
    return output

async def create_generation(new_generation: models.GenerationStart, request: Request, ):
    response = await http_client.put(
        f"{BACKEND_URL}round/{new_generation.round_id}",
        json=new_generation.model_dump(),
        headers={"Content-Type": "application/json",
        },
        auth=get_auth(request),
    )
    if response.status_code != 200:
        return None
    output = models.GenerationCorrectSentence(**response.json())
    return output

async def get_interpretation(round_id: int, interpretation: models.GenerationCorrectSentence, request: Request, ):
    # Test get interpretation
    response = await http_client.put(
        f"{BACKEND_URL}round/{round_id}/interpretation",
        json=interpretation.model_dump(),
        headers={"Content-Type": "application/json",
        },
        auth=get_auth(request),
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
    return response

async def complete_generation(round_id: int, generation: models.GenerationCompleteCreate, request: Request, ):
    #Test get scores
    response = await http_client.put(
        f"{BACKEND_URL}round/{round_id}/complete",
        json=generation.model_dump(),
        headers={"Content-Type": "application/json",
        },
        auth=get_auth(request),
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