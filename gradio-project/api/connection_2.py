import os, json, base64
import httpx, threading, asyncio
from httpx_ws import aconnect_ws
import gradio as gr
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, Request, Depends, status, HTTPException
from websockets.exceptions import ConnectionClosed
from typing import Annotated, Optional
from PIL import Image as PILImage
import io, datetime, time, zoneinfo
from logging import getLogger, FileHandler, Formatter
from wsproto.utilities import LocalProtocolError

filehandler = FileHandler("logs/connection_2.log", mode="a", encoding=None, delay=False)
filehandler.setFormatter(
    Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger = getLogger(__name__)
logger.setLevel("DEBUG")
logger.addHandler(filehandler)

from api import models

BACKEND_URL = os.getenv("BACKEND_URL_2")

http_client = httpx.AsyncClient()

class BearerAuth(httpx.Auth):
    requires_request_body = True

    def __init__(self, access_token, refresh_token, refresh_url):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.refresh_url = refresh_url
        self._sync_lock = threading.RLock()
        self._async_lock = asyncio.Lock()

    def sync_get_token(self):
        with self._sync_lock:
            response = http_client.post(
                self.refresh_url,
                data={"refresh_token": self.refresh_token}
            )
            response.raise_for_status()
        return response

    def sync_auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.access_token}"
        response = yield request

        if response.status_code == 401:
            refresh_response = self.sync_get_token()
            self.update_tokens(refresh_response.json())

            request.headers["Authorization"] = f"Bearer {self.access_token}"
            yield request

    async def async_get_token(self):
        async with self._async_lock:
            response = await http_client.post(
                self.refresh_url,
                data={"refresh_token": self.refresh_token}
            )
            response.raise_for_status()
        return response

    async def async_auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.access_token}"
        response = yield request

        if response.status_code == 401:
            refresh_response = await self.async_get_token()
            self.update_tokens(refresh_response.json())

            request.headers["Authorization"] = f"Bearer {self.access_token}"
            yield request

    def update_tokens(self, response):
        self.access_token = response["access_token"]

def convert_json(mdl: models.BaseModel):
    json_data = mdl.model_dump()
    if "created_at" in json_data:
        json_data["created_at"] = json_data["created_at"].isoformat()
    if "at" in json_data:
        json_data["at"] = json_data["at"].isoformat()
    if "published_at" in json_data:
        json_data["published_at"] = json_data["published_at"].isoformat()
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

def decode_image(image_str: str):
    b = str.encode(image_str)
    imgdata = base64.b64decode(b)
    return PILImage.open(io.BytesIO(imgdata))

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
        raise HTTPException(status_code=e.response.status_code, detail=e.response.json())

def get_auth(request: Request):
    if hasattr(request, "session") and "token" in request.session:
        bearer = BearerAuth(
            access_token=request.session["token"]["access_token"],
            refresh_token=request.session["token"]["refresh_token"],
            refresh_url=f"{BACKEND_URL}refresh_token"
        )
        return bearer
    else:
        raise HTTPException(status_code=401, detail="Not authenticated")

async def read_leaderboard(
        request: Request, 
        published_at_start: Optional[datetime.datetime] = None,
        published_at_end: Optional[datetime.datetime] = datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo")),
        is_admin: Optional[bool] = False
):
    auth = get_auth(request)
    if is_admin:
        url = f"{BACKEND_URL}leaderboards/admin/"
    else:
        url = f"{BACKEND_URL}leaderboards"

    if published_at_start:
        url += f"?published_at_start={published_at_start.strftime('%d%m%Y')}"

    if published_at_end:
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

        if is_admin:
            output = [models.Leaderboard(
                **leaderboard,
            ) for leaderboard in response.json()]
        else:
            output = [models.Leaderboard(
                **leaderboard[0],
            ) for leaderboard in response.json()]
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

async def update_leaderboard(
        new_leaderboard: models.LeaderboardUpdate, 
        request: Request
):
    json_data = convert_json(new_leaderboard)
    response = await http_client.put(
        f"{BACKEND_URL}leaderboards/{new_leaderboard.id}",
        json=json_data,
        auth=get_auth(request),
    )
    response.raise_for_status()
    output = models.Leaderboard(**response.json())
    return output

async def get_schools(
        leaderboard_id: int, 
        request: Request
):
    response = await http_client.get(
        f"{BACKEND_URL}leaderboards/{leaderboard_id}/schools",
        auth=get_auth(request),
        follow_redirects=True
    )
    response.raise_for_status()
    output = [school['school'] for school in response.json()]
    return output

async def get_original_images(leaderboard_id: int, request: Request):
    response = await http_client.get(
        f"{BACKEND_URL}original_image/{leaderboard_id}",
        auth=get_auth(request),
        timeout=120
    )
    response.raise_for_status()
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
    response.raise_for_status()
    output = models.RoundStartOut(**response.json())
    return output
    
async def read_my_rounds(request: Request, is_completed: bool = False, leaderboard_id: int = None, program: str = "none"):
    if leaderboard_id is None:
        url = f"{BACKEND_URL}my_rounds/?is_completed={is_completed}&program={program}"
    else:
        url = f"{BACKEND_URL}my_rounds/?is_completed={is_completed}&leaderboard_id={leaderboard_id}&program={program}"

    response = await http_client.get(
        url,
        auth=get_auth(request),
    )
    response.raise_for_status()
    output = [models.Round(**round) for round in response.json()]
    return output

async def read_my_generations(request: Request, leaderboard_id: int = None):
    if leaderboard_id is None:
        url = f"{BACKEND_URL}my_generations"
    else:
        url = f"{BACKEND_URL}my_generations/?leaderboard_id={leaderboard_id}"

    response = await http_client.get(
        url,
        auth=get_auth(request),
    )
    response.raise_for_status()
    output = [models.GenerationRound(
        generation=generation[0],
        round=generation[1]
    ) for generation in response.json()]
    return output

class Play_Round_WS:

    async def get_ws_token(self, request: Request):
        """
        Get the websocket token from the backend
        """
        if hasattr(request, "session") and "token" in request.session:
            url = f"{BACKEND_URL}ws_token"
            response = await http_client.post(
                url, 
                auth=get_auth(request)
            )
            response.raise_for_status()
            ws_token = response.json()
            return ws_token['ws_token']
        else:
            raise HTTPException(status_code=401, detail="Not authenticated")

    @classmethod
    async def create(cls, leaderboard_id, request: Request, program: str = "none"):
        instance = cls()
        instance.program = program

        # Get WebSocket token
        instance.url = f"{BACKEND_URL}ws/{leaderboard_id}?token={await instance.get_ws_token(request)}"
        
        return instance
        
    def __init__(self):
        self.ws = None
        self.program = None
        self.resume_round = None
        self.url = None
        self._ws_context = None
        self._closed = False

    async def send_json(self, json_data):
        """Send JSON data to WebSocket with automatic reconnection"""
        
        # convert json to text
        text_data = json.dumps(json_data)
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                # send text data to websocket
                await self.ws.send_text(text_data)
                return
            except Exception as e:
                logger.error(f"Error sending data to websocket: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error sending data to websocket"
                )

    async def receive_json(self):
        """Receive JSON data from WebSocket with automatic reconnection"""
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # receive text data from websocket
                text_data = await self.ws.receive_text()

                # convert text data to json
                json_data = json.loads(text_data)
                return json_data
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received from WebSocket: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Invalid JSON received from WebSocket"
                )
            except Exception as e:
                logger.error(f"Unexpected error receiving WebSocket data: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error receiving data from WebSocket"
                )

    async def start_resume(self, new_round: models.RoundStart, resume: bool = False)-> models.Response:
        leaderboard_id = new_round.leaderboard_id

        if resume: 
            send_data = {
                    "action": "resume",
                    "program": new_round.program,
                    "obj": convert_json(new_round),
                }
        else:
            send_data = {
                    "action": "start",
                    "program": new_round.program,
                    "obj": convert_json(new_round),
                }
            
        async with aconnect_ws(
            self.url
        ) as self.ws:
            await self.send_json(send_data)
            send_data["action"] = "resume"
            self.resume_round = send_data
                
            response = await self.receive_json()

        self.original_image = PILImage.open(
            io.BytesIO(
                base64.b64decode(
                    response['leaderboard']['image']
                )
                
            )
        )
        response = models.Response(**response)
        return response
    
    async def resume(self):
        await self.send_json(
            self.resume_round
        )
        await self.receive_json()
        return

    async def send_message(self, new_message:models.MessageSend)-> models.Response:
        async with aconnect_ws(
            self.url
        ) as self.ws:
            await self.resume()

            await self.send_json(
                {
                    "action": "hint",
                    "program": self.program,
                    "obj": convert_json(new_message),
                }
            )
            response = await self.receive_json()
        response = models.Response(**response)
        return response
    
    async def send_answer(self, new_generation: models.GenerationStart)-> models.Response:
        async with aconnect_ws(
            self.url
        ) as self.ws:
            await self.resume()
            await self.send_json(
                {
                    "action": "submit",
                    "program": self.program,
                    "obj": convert_json(new_generation),
                }
            )
            response = await self.receive_json()
        response = models.Response(**response)
        return response
    
    async def evaluate(self)-> models.Response:
        async with aconnect_ws(
            self.url
        ) as self.ws:
            await self.resume()
            await self.send_json(
                {
                    "action": "evaluate",
                }
            )
            while True:
                response = await self.receive_json()
                response = models.Response(**response)
                if not(response.feedback and response.feedback=="waiting"):
                    break
        return response
    
    async def end(self)-> models.Response:
        async with aconnect_ws(
            self.url
        ) as self.ws:
            await self.resume()
            # send end action
            await self.send_json(
                {
                    "action": "end",
                }
            )
            response = await self.receive_json()
        response = models.Response(**response)
        return response
            
async def send_message(round_id: int, new_message:models.MessageSend, request: Request, ):
    json_data = convert_json(new_message)
    response = await http_client.put(
        f"{BACKEND_URL}round/{round_id}/chat",
        json=json_data,
        headers={"Content-Type": "application/json",
        },
        auth=get_auth(request),
        timeout=40
    )
    response.raise_for_status()
    output = models.Chat(**response.json())
    return output

async def get_chat(round_id: int, request: Request, ):
    response = await http_client.get(
        f"{BACKEND_URL}chat/{round_id}",
        auth=get_auth(request),
    )
    response.raise_for_status()
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
        timeout=120
    )
    if response.status_code == 400:
        logger.debug(f"create_generation: {response.json()}")
        return None
    response.raise_for_status()
    
    output = models.GenerationCorrectSentence(**response.json())
    
    return output

async def get_interpretation(round_id: int, interpretation: models.GenerationCorrectSentence, request: Request, ):
    retry_delay = 10
    timeout = time.time() + 120
    
    # get interpretation
    response = await http_client.put(
        f"{BACKEND_URL}round/{round_id}/interpretation",
        json=interpretation.model_dump(),
        headers={"Content-Type": "application/json",
        },
        auth=get_auth(request),
        timeout=120
    )
    response.raise_for_status()

    generation_id = interpretation.id

    # wait for interpretation to finish
    while True:
        await asyncio.sleep(retry_delay)
        if time.time() > timeout:
            raise HTTPException(status_code=500, detail="Interpretation took too long")
        response = await http_client.get(
            f"{BACKEND_URL}tasks/generation/{generation_id}",
            timeout=120
        )
        response.raise_for_status()
        output = response.json()
        if output["status"] == "FINISHED" or len(output["tasks"])==0:
            break
    
    return True

async def get_interpreted_image(generation_id: int, request: Request):
    """
    Get the interpreted image with improved error handling and retry logic
    
    Args:
        generation_id (int): ID of the generation
        request (Request): Request object
        
    Returns:
        PIL.Image or None: The interpreted image if successful, None if failed after retries
    """
    max_retries = 30
    retry_delay = 5  # seconds
    timeout = 300  # seconds per request
    
    for attempt in range(max_retries):
        try:
            response = await http_client.get(
                f"{BACKEND_URL}interpreted_image/{generation_id}",
                auth=get_auth(request),
                timeout=timeout
            )
            
            if response.status_code == 200:
                return PILImage.open(io.BytesIO(response.content))
                
            # If status code is not 200, wait before retrying
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                await asyncio.sleep(retry_delay)
                
        except (httpx.TimeoutException, httpx.RemoteProtocolError) as e:
            # Log error if needed
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                await asyncio.sleep(retry_delay)
            continue
            
        except Exception as e:
            # For any other unexpected errors, return None
            logger.debug(f"get_interpreted_image: {e}")
            continue
    logger.debug(f"get_interpreted_image: Failed after {max_retries} attempts")
    return None

async def obtain_evaluation_from_past(generation_id: int, request: Request):
    """
    Get the interpreted image with improved error handling and retry logic
    
    Args:
        generation_id (int): ID of the generation
        request (Request): Request object
        
    Returns:
        string
    """
    max_retries = 30
    retry_delay = 5  # seconds
    timeout = 300  # seconds per request
    
    for attempt in range(max_retries):
        try:
            response = await http_client.get(
                f"{BACKEND_URL}evaluation_msg/{generation_id}",
                auth=get_auth(request),
                timeout=timeout
            )
            
            if response.status_code == 200:
                return response.json()['content']
                
            # If status code is not 200, wait before retrying
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                await asyncio.sleep(retry_delay)
                
        except (httpx.TimeoutException, httpx.RemoteProtocolError) as e:
            # Log error if needed
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                await asyncio.sleep(retry_delay)
            continue
            
        except Exception as e:
            # For any other unexpected errors, return None
            logger.debug(f"get_evaluation_msg: {e}")
            continue
    logger.debug(f"get_evaluation_msg: Failed after {max_retries} attempts")
    return None

async def complete_generation(round_id: int, generation_id: int, request: Request, ):
    """
    Check whether the generation is complete and return the details
    """
    max_retries = 10
    retry_delay = 5  # seconds
    timeout = 120  # seconds per request
    generation= models.GenerationCompleteCreate(
        id=generation_id,
        at=datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo"))
    )
    
    for attempt in range(max_retries):
        try:
            json_data = convert_json(generation)
            response = await http_client.put(
                f"{BACKEND_URL}round/{round_id}/complete",
                json=json_data,
                headers={"Content-Type": "application/json",
                },
                auth=get_auth(request),
                timeout=timeout
            )
            
            if response.status_code == 200:
                output = models.GenerationComplete(**response.json())
                if output.is_completed == True:
                    return output
                
            # If status code is not 200, wait before retrying
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                await asyncio.sleep(retry_delay)
                
        except (httpx.TimeoutException, httpx.RemoteProtocolError) as e:
            # Log error if needed
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                await asyncio.sleep(retry_delay)
            continue
            
        except Exception as e:
            # For any other unexpected errors, return None
            logger.debug(f"complete_generation: {e}")
            continue
    logger.debug(f"complete_generation: Failed after {max_retries} attempts")
    return None

async def end_round(round_id: int, request: Request, ):
    # Test complete round
    response = await http_client.post(
        f"{BACKEND_URL}round/{round_id}/end",
        headers={"Content-Type": "application/json",
        },
        auth=get_auth(request),
    )
    response.raise_for_status()
    output = models.Round(**response.json())
    return output

async def get_score(generation_id: int, request: Request, ):
    """
    Check whether the generation is complete and return the details
    """
    max_retries = 10
    retry_delay = 5  # seconds
    timeout = 120  # seconds per request
    
    for attempt in range(max_retries):
        try:
            response = await http_client.get(
                f"{BACKEND_URL}generation/{generation_id}/score/",
                auth=get_auth(request),
                timeout=timeout,
                follow_redirects=True
            )
            
            if response.status_code == 200:
                output = models.Score(**response.json())
                if output.image_similarity is not None:
                    return output
                
            # If status code is not 200, wait before retrying
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                await asyncio.sleep(retry_delay)
                
        except (httpx.TimeoutException, httpx.RemoteProtocolError) as e:
            # Log error if needed
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                await asyncio.sleep(retry_delay)
            continue
            
        except Exception as e:
            # For any other unexpected errors, return None
            logger.debug(f"get_score: {e}")
            continue
    logger.debug(f"get_score: Failed after {max_retries} attempts")
    return None

async def get_rounds(leaderboard_id: int, request: Request):
    response = await http_client.get(
        f"{BACKEND_URL}leaderboards/{leaderboard_id}/rounds",
        auth=get_auth(request),
        follow_redirects=True
    )
    response.raise_for_status()
    output = [models.Round(**round) for round in response.json()]
    return output

async def get_generation(generation_id: int, request: Request):
    response = await http_client.get(
        f"{BACKEND_URL}generation/{generation_id}",
        auth=get_auth(request),
    )
    response.raise_for_status()
    output = models.GenerationOut(**response.json())
    return output

async def get_generation_score(generation_id: int, request: Request):
    response = await http_client.get(
        f"{BACKEND_URL}generation/{generation_id}/score",
        auth=get_auth(request),
    )
    response.raise_for_status()
    return response.json()

async def check_playable(
        leaderboard_id: int, 
        request: Request,
):
    program = request.session.get("program", 'none')
    response = await http_client.get(
        f"{BACKEND_URL}leaderboards/{leaderboard_id}/playable/?program={program}",
        auth=get_auth(request),
        follow_redirects=True
    )
    
    response.raise_for_status()
    return response.json()['is_playable']

async def get_users(request: Request):
    response = await http_client.get(
        f"{BACKEND_URL}users",
        auth=get_auth(request),
    )
    response.raise_for_status()
    output = [models.User(**user) for user in response.json()]
    return output

async def get_generations(
    request: Request,
    leaderboard_id: Optional[int] = None, 
    player_id: Optional[int] = None, 
    school_name: Optional[str] = None
):
    if hasattr(request, "session"):
        program = request.session.get("program", 'none')
    else:
        program = 'none'
    url = "{}generations/?program={}".format(BACKEND_URL, program)
    if school_name:
        url+= f"&school_name={school_name}"
    if leaderboard_id:
        url+= f"&leaderboard_id={leaderboard_id}"
    if player_id:
        url+= f"&player_id={player_id}"

    response = await http_client.get(
        url,
        auth=get_auth(request),
    )
    response.raise_for_status()
    output = [models.GenerationRound(
        generation=generation[0],
        round=generation[1]
    ) for generation in response.json()]
    return output