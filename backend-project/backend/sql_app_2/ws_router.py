import logging.config
from fastapi import Depends, APIRouter, HTTPException, responses, status, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates
import os
import zoneinfo
from threading import RLock

from fastapi.security import OAuth2PasswordRequestForm
from pydantic import parse_obj_as
from sqlalchemy.orm import Session
import datetime, json, asyncio #, yappi
import numpy as np
from cachetools import TTLCache

from . import crud, schemas
from tasks import app as celery_app
from tasks import generateDescription2, generate_interpretation2, calculate_score_gpt
from .database import SessionLocal2, engine2

from .dependencies import sentence, openai_chatbot
from .authentication import authenticate_user, authenticate_user_2, create_access_token, oauth2_scheme, SECRET_KEY_WS, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, create_refresh_token, JWTError, jwt, create_ws_token
from util import *

from typing import Annotated, Optional
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
    prefix="/ws",
)

JST = zoneinfo.ZoneInfo("Asia/Tokyo")

WS_USER_CACHE_TTL = int(os.getenv("WS_USER_CACHE_TTL", os.getenv("USER_CACHE_TTL", "10")))
WS_USER_CACHE_MAXSIZE = int(os.getenv("WS_USER_CACHE_MAXSIZE", os.getenv("USER_CACHE_MAXSIZE", "2048")))

ws_user_cache = TTLCache(maxsize=WS_USER_CACHE_MAXSIZE, ttl=WS_USER_CACHE_TTL)
ws_user_cache_lock = RLock()


def _get_cached_user(username: str) -> Optional[schemas.User]:
    with ws_user_cache_lock:
        return ws_user_cache.get(username)


def _cache_user(username: str, user: schemas.User) -> None:
    with ws_user_cache_lock:
        ws_user_cache[username] = user


async def _load_user_by_username(db: Session, username: str) -> Optional[schemas.User]:
    cached_user = _get_cached_user(username)
    if cached_user:
        return cached_user

    db_user = await asyncio.to_thread(crud.get_user_by_username, db, username=username)
    if db_user is None:
        return None

    user_schema = schemas.User.model_validate(db_user, from_attributes=True)
    if user_schema.is_active:
        _cache_user(username, user_schema)
    return user_schema

async def get_current_user_ws(db: Annotated[Session, Depends(get_db)],token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY_WS, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = schemas.TokenData(username=username)
        except JWTError:
            raise credentials_exception
        except jwt.ExpiredSignatureError:
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
        user = await _load_user_by_username(db, token_data.username)
        if user is None:
            raise credentials_exception
        elif user.is_active:
            return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    else:
        raise credentials_exception

@router.websocket("/{leaderboard_id}")
async def round_websocket(
    websocket: WebSocket,
    leaderboard_id: int,
    token: str,
    db: Session = Depends(get_db),
):
    current_user = await get_current_user_ws(db=db, token=token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Login to connect")

    player_id = current_user.id

    start_time = datetime.datetime.now(tz=JST)
    duration = 0
    db_round = None
    db_generation = None
    chatbot_obj = None
    chain_result = None
    # accept the websocket connection and record in database
    crud.create_user_action(
        db=db,
        user_action=schemas.UserActionBase(
            user_id=player_id,
            action="connect websocket",
            sent_at=start_time,
            received_at=start_time,
        )
    )
    await websocket.accept()
    try:
        user_action = await websocket.receive_json()
        db_user_action = crud.create_user_action(
            db=db,
            user_action=schemas.UserActionBase(
                user_id=player_id,
                action=user_action["action"],
                received_at=start_time,
                sent_at=start_time,
            )
        )
    except WebSocketDisconnect:
        # client disconnected immediately after connecting; record and exit gracefully
        crud.create_user_action(
            db=db,
            user_action=schemas.UserActionBase(
                user_id=player_id,
                action="disconnect websocket",
                sent_at=datetime.datetime.now(tz=JST),
                received_at=datetime.datetime.now(tz=JST),
            )
        )
        logger1.info(f"WebSocket disconnected for user {player_id} before initial message")
        return
    except Exception as e:
        logger1.error(f"Error during websocket initial receive: {str(e)}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
        return

    # set program
    obj = parse_obj_as(schemas.RoundCreate, user_action['obj'])
    db_program_user = crud.get_programs_by_user(
        db=db,
        user_id=player_id,
    )

    db_program = crud.get_program_by_name(db, obj.program)
    if not db_program_user:
        db_program = crud.get_program_by_name(db, "inlab_test")
    elif not (db_program and db_program.id in [pu.program_id for pu in db_program_user]):
        db_program = db_program_user[0].program

    # if user resumes the round
    if user_action["action"] == "resume":
        leaderboard_id = user_action["obj"]["leaderboard_id"]

        unfinished_rounds = crud.get_rounds(
            db=db,
            player_id=player_id,
            leaderboard_id=leaderboard_id,
            is_completed=False,
            program_id=db_program.id
        )
        finished_rounds = crud.get_rounds(
            db=db,
            player_id=player_id,
            leaderboard_id=leaderboard_id,
            is_completed=True,
            program_id=db_program.id
        )

        if unfinished_rounds:
            db_round = crud.get_round(
                db=db,
                round_id=unfinished_rounds[0].id,
            )
            db_leaderboard = crud.get_leaderboard(db=db, leaderboard_id=leaderboard_id)

            db_generation = crud.get_generation(db=db, generation_id=db_round.last_generation_id)
            db_chat = crud.get_chat(db=db, chat_id=db_round.chat_history)
            prev_res_ids = [
                msg.response_id for msg in db_chat.messages if msg.response_id is not None
            ]
            chatbot_obj = openai_chatbot.Hint_Chatbot(
                model_name=db_round.model,
                vocabularies=db_leaderboard.vocabularies,
                first_res_id=db_leaderboard.response_id,
                prev_res_id=prev_res_ids[-1] if prev_res_ids else db_leaderboard.response_id,
                prev_res_ids=prev_res_ids
            )

            db_score = crud.get_score(db=db, generation_id=db_generation.id)

            if not db_generation.is_completed:
                generated_time = db_generation.generated_time
                duration += db_generation.duration
            else:
                generated_time = db_generation.generated_time + 1
                db_generation = crud.create_generation(
                    db=db,
                    round_id=db_round.id,
                    generation=schemas.GenerationCreate(
                        round_id=db_round.id,
                        sentence='',
                        generated_time=generated_time,
                        created_at=start_time,
                    )
                )

            # prepare data to send
            send_data = {
                "feedback": db_program.feedback,
                "leaderboard": {
                    "id": leaderboard_id,
                    "image": db_round.leaderboard.original_image.image,
                },
                "round": {
                    "id": db_round.id,
                    "display_name": db_round.display_name,
                    "generated_time":generated_time,
                    "generations": [
                        g.id for g in db_round.generations if g.is_completed
                    ]
                },
                "generation": {
                    "id": db_generation.id,
                    "interpreted_image": db_generation.interpreted_image.image if db_generation.interpreted_image else None,
                    "generated_time": db_generation.generated_time,
                    "sentence": db_generation.sentence,
                    "correct_sentence": db_generation.correct_sentence,
                    "is_completed": db_generation.is_completed,
                    "image_similarity": db_score.image_similarity if db_score else None,
                    "duration": duration,
                },
                "chat": {
                    "id": db_round.chat_history,
                    "messages" : [
                        {
                            'id': db_message.id,
                            'sender': db_message.sender,
                            'content': db_message.content,
                            'created_at': db_message.created_at.isoformat(),
                            'is_hint': db_message.is_hint
                        }
                        for db_message in db_chat.messages
                    ]
                },
            }
        elif finished_rounds:
            db_round = crud.get_round(
                db=db,
                round_id=finished_rounds[0].id,
            )
            db_leaderboard = crud.get_leaderboard(db=db, leaderboard_id=leaderboard_id)

            db_generation = crud.get_generation(db=db, generation_id=db_round.last_generation_id)
            db_chat = crud.get_chat(db=db, chat_id=db_round.chat_history)
            prev_res_ids = [
                msg.response_id for msg in db_chat.messages if msg.response_id is not None
            ]
            chatbot_obj = openai_chatbot.Hint_Chatbot(
                model_name=db_round.model,
                vocabularies=db_leaderboard.vocabularies,
                first_res_id=db_leaderboard.response_id,
                prev_res_id=prev_res_ids[-1] if prev_res_ids else db_leaderboard.response_id,
                prev_res_ids=prev_res_ids
            )
            generated_time = db_generation.generated_time

            db_score = crud.get_score(db=db, generation_id=db_generation.id)

            # prepare data to send
            send_data = {
                "feedback": db_program.feedback,
                "leaderboard": {
                    "id": leaderboard_id,
                    "image": db_round.leaderboard.original_image.image,
                },
                "round": {
                    "id": db_round.id,
                    "display_name": db_round.display_name,
                    "generated_time":generated_time,
                    "generations": [
                        g.id for g in db_round.generations if g.is_completed
                    ]
                },
                "generation": {
                    "id": db_generation.id,
                    "interpreted_image": db_generation.interpreted_image.image if db_generation.interpreted_image else None,
                    "generated_time": db_generation.generated_time,
                    "sentence": db_generation.sentence,
                    "correct_sentence": db_generation.correct_sentence,
                    "is_completed": db_generation.is_completed,
                    "image_similarity": db_score.image_similarity if db_score else None,
                },
                "chat": {
                    "id": db_round.chat_history,
                    "messages" : [
                        {
                            'id': db_message.id,
                            'sender': db_message.sender,
                            'content': db_message.content,
                            'created_at': db_message.created_at.isoformat(),
                            'is_hint': db_message.is_hint
                        }
                        for db_message in db_chat.messages
                    ]
                },
            }
        else:
            user_action["action"] = "start"
    elif user_action["action"] not in ["start", "resume"]:
        logger1.error(f"Unknown initial action '{user_action['action']}' from user {player_id}")
        send_data = {}

    if user_action["action"] == "start":

        db_leaderboard = crud.get_leaderboard(db, leaderboard_id=leaderboard_id)
        db_score = None

        if db_program is None:
            db_round = crud.create_round(
                db=db,
                leaderboard_id=leaderboard_id,
                user_id=player_id,
                model_name=obj.model,
                created_at=obj.created_at,
            )

        else:
            db_round = crud.create_round(
                db=db,
                leaderboard_id=leaderboard_id,
                user_id=player_id,
                program_id=db_program.id,
                model_name=obj.model,
                created_at=obj.created_at,
            )

        db_generation = crud.create_generation(
            db=db,
            round_id=db_round.id,
            generation=schemas.GenerationCreate(
                round_id=db_round.id,
                sentence='',
                generated_time=0,
                created_at=start_time,
            )
        )

        db_message = crud.create_message(
            db=db,
            message=schemas.MessageBase(
                content="画像を説明する際にヒントが使えます。下の『Averyへのメッセージ🤖』に質問したい内容を入力してくださいね！",
                sender="assistant",
                created_at=datetime.datetime.now(tz=JST),
                is_hint=False
            ),
            chat_id=db_round.chat_history
        )['message']

        chatbot_obj = openai_chatbot.Hint_Chatbot(
            model_name=obj.model,
            vocabularies=db_leaderboard.vocabularies,
            first_res_id=db_leaderboard.response_id,
            prev_res_id=db_leaderboard.response_id
        )

        generated_time = 0

        # prepare data to send
        send_data = {
            "feedback": db_program.feedback,
            "leaderboard": {
                "id": leaderboard_id,
                "image": db_round.leaderboard.original_image.image,
            },
            "round": {
                "id": db_round.id,
                "display_name": db_round.display_name,
                "generated_time":generated_time,
                "generations": []
            },
            "generation": {
                "id": db_generation.id,
                "interpreted_image": db_generation.interpreted_image.image if db_generation.interpreted_image else None,
                "generated_time": db_generation.generated_time,
                "correct_sentence": db_generation.correct_sentence,
                "is_completed": db_generation.is_completed,
                "image_similarity": db_score.image_similarity if db_score else None,
            },
            "chat": {
                "id": db_round.chat_history,
                "messages" : [
                    {
                        'id': db_message.id,
                        'sender': db_message.sender,
                        'content': db_message.content,
                        'created_at': db_message.created_at.isoformat(),
                        'is_hint': db_message.is_hint
                    }
                ]
            },
        }

    await websocket.send_json(send_data)

    crud.update_user_action(
        db=db,
        user_action=schemas.UserActionUpdate(
            id=db_user_action.id,
            related_id=db_generation.id if db_generation else None,
            sent_at=datetime.datetime.now(tz=JST),
        )
    )

    try:
        # yappi.clear_stats()
        # yappi.set_clock_type("wall")
        # yappi.start()
        while True:
            user_action = await websocket.receive_json()

            db_user_action = crud.create_user_action(
                db=db,
                user_action=schemas.UserActionBase(
                    user_id=player_id,
                    action=user_action["action"],
                    related_id=db_generation.id if db_generation else None,
                    received_at=datetime.datetime.now(tz=JST),
                    sent_at=datetime.datetime.now(tz=JST),
                )
            )

            # if user asks for a hint
            if user_action["action"] == "hint":
                db_messages = []
                obj = parse_obj_as(schemas.MessageReceive, user_action['obj'])
                crud.create_message(
                    db=db,
                    message=schemas.MessageBase(
                        content=obj.content,
                        sender="user",
                        created_at=datetime.datetime.now(tz=JST),
                        is_hint=True
                    ),
                    chat_id=db_round.chat_history
                )

                # run in threadpool to avoid blocking event loop
                # chatbot_obj.nextResponse: ask_for_hint, new_messages, base64_image
                hint = await asyncio.to_thread(
                    chatbot_obj.nextResponse,
                    obj.content,
                    [],
                    db_round.leaderboard.original_image.image,
                )

                db_messages.append(
                    crud.create_message(
                        db=db,
                        message=schemas.MessageBase(
                            content=hint,
                            sender="assistant",
                            created_at=datetime.datetime.now(tz=JST),
                            is_hint=True,
                            response_id=chatbot_obj.prev_res_id
                        ),
                        chat_id=db_round.chat_history
                    )['message']
                )

                send_data = {
                    "chat": {
                        "id": db_round.chat_history,
                        "messages" : [
                            {
                                'id': db_message.id,
                                'sender': db_message.sender,
                                'content': db_message.content,
                                'created_at': db_message.created_at.isoformat(),
                                'is_hint': db_message.is_hint
                            }
                            for db_message in db_messages
                        ]
                    },
                }

            elif user_action["action"] == "change_display_name":
                obj = parse_obj_as(schemas.RoundUpdateName, user_action['obj'])
                db_round = crud.update_round_display_name(
                    db=db,
                    round_update=obj
                )

                send_data = {
                    "round": {
                        "id": db_round.id,
                        "display_name": db_round.display_name,
                        "generated_time":generated_time,
                    },
                }

            # if user submits the answer
            elif user_action["action"] == "submit":
                obj = parse_obj_as(schemas.GenerationCreate, user_action['obj'])
                status = 0
                sentences = [
                    g.sentence.strip() for g in db_round.generations if g.sentence != '' and g.correct_sentence is not None and g.id != db_generation.id
                ]

                if db_generation.correct_sentence is None:
                    db_generation = crud.update_generation0(
                        db=db,
                        generation=obj,
                        generation_id=db_generation.id
                    )
                elif obj.sentence.strip() in sentences:
                    db_generation = crud.get_generation(db=db, generation_id=db_generation.id)
                    status = 3
                else:
                    generated_time += 1
                    obj.generated_time = generated_time
                    db_generation = crud.create_generation(
                        db=db,
                        round_id=db_round.id,
                        generation=obj,
                    )

                if status != 3:
                    try:
                        status, correct_sentence, spelling_mistakes, grammar_mistakes=await asyncio.to_thread(
                            sentence.checkSentence,
                            db_generation.sentence
                        )
                    except Exception as e:
                        logger1.error(f"Error in get_user_answer: {str(e)}")
                        raise HTTPException(status_code=400, detail=str(e))


                if status == 0:
                    crud.update_generation3(
                        db=db,
                        generation=schemas.GenerationComplete(
                            id=db_generation.id,
                            grammar_errors=str(grammar_mistakes),
                            spelling_errors=str(spelling_mistakes),
                            n_grammar_errors=len(grammar_mistakes),
                            n_spelling_errors=len(spelling_mistakes),
                            updated_grammar_errors=True,
                            is_completed=False
                        )
                    )

                    duration += (datetime.datetime.now(tz=JST) - start_time).total_seconds()

                    crud.update_generation_duration(
                        db=db,
                        generation_id=db_generation.id,
                        duration=duration
                    )
                    duration = 0

                    db_generation = crud.update_generation1(
                        db=db,
                        generation=schemas.GenerationCorrectSentence(
                            id=db_generation.id,
                            correct_sentence=correct_sentence
                        )
                    )

                    messages = [
                        schemas.MessageBase(
                            content="""回答を記録しました。📝
あなたの回答（画像生成に参考された）: {}\n\n修正された回答：{}""".format(db_generation.sentence, db_generation.correct_sentence),
                            sender="assistant",
                            created_at=datetime.datetime.now(tz=JST),
                            is_hint=False
                        )
                    ]

                    # server-side processing
                    generation_dict = {
                        "id": db_generation.id,
                        "at": db_generation.created_at,
                    }

                    if "IMG" in db_program.feedback and "AWS" in db_program.feedback:
                        chain_interpretation = celery_app.chain(
                            celery_app.group(
                                generate_interpretation2.s(generation_id=db_generation.id, sentence=db_generation.sentence, at=db_generation.created_at),
                            ),
                            celery_app.group(
                                calculate_score_gpt.s(),
                            ),
                        )
                        chain_result = await chain_interpretation.apply_asyncx()
                    elif "IMG" in db_program.feedback:
                        chain_interpretation = celery_app.chain(
                            celery_app.group(
                                generate_interpretation2.s(generation_id=db_generation.id, sentence=db_generation.sentence, at=db_generation.created_at),
                            )
                        )
                        chain_result = await chain_interpretation.apply_asyncx()
                    elif "AWS" in db_program.feedback:
                        chain_interpretation = celery_app.chain(
                            celery_app.group(
                                calculate_score_gpt.s(items=generation_dict),
                            ),
                        )
                        chain_result = await chain_interpretation.apply_asyncx()
                    else:
                        chain_result = None


                elif status == 1:
                    messages = [
                        schemas.MessageBase(
                            content="ブー！英語で答えてください。",
                            sender="assistant",
                            created_at=datetime.datetime.now(tz=JST),
                            is_hint=False
                        )
                    ]

                elif status == 2:
                    messages = [
                        schemas.MessageBase(
                            content="ブー！不適切な言葉が含まれています。",
                            sender="assistant",
                            created_at=datetime.datetime.now(tz=JST),
                            is_hint=False
                        )
                    ]

                elif status == 3:
                    messages = [
                        schemas.MessageBase(
                            content="ブー！同じ回答がすでに提出されています。新しいアイデアを試してみましょう！",
                            sender="assistant",
                            created_at=datetime.datetime.now(tz=JST),
                            is_hint=False
                        )
                    ]
                else:
                    messages = []

                db_messages = []

                for message in messages:
                    db_messages.append(
                        crud.create_message(
                            db=db,
                            message=message,
                            chat_id=db_round.chat_history
                        )['message']
                    )

                # prepare data to send
                send_data = {
                    "leaderboard": {
                        "id": leaderboard_id,
                        "image": db_round.leaderboard.original_image.image,
                    },
                    "round": {
                        "id": db_round.id,
                        "display_name": db_round.display_name,
                        "generated_time":generated_time,
                    },
                    "chat": {
                        "id": db_round.chat_history,
                        "messages" : [
                            {
                                'id': db_message.id,
                                'sender': db_message.sender,
                                'content': db_message.content,
                                'created_at': db_message.created_at.isoformat(),
                                'is_hint': db_message.is_hint
                            }
                            for db_message in db_messages
                        ]
                    },
                    "generation": {
                        "id": db_generation.id,
                        "correct_sentence": db_generation.correct_sentence if status == 0 else None,
                        "duration": duration,
                    }
                }

            elif user_action["action"] == "evaluate" and (db_generation.correct_sentence is None or db_generation.correct_sentence == ""):
                send_data = {}
            elif user_action["action"] == "evaluate":

                if "IMG" in db_program.feedback and db_generation.interpreted_image is None:
                    # If the interpreted image is not generated, log an error
                    logger1.error(f"Interpreted image not found for generation {db_generation.id}")

                if "AWS" in db_program.feedback:
                    db_score = db_generation.score
                    if db_score is not None:
                        image_similarity = db_score.image_similarity
                        scores_dict = {
                            'grammar_score': db_score.grammar_score,
                            'spelling_score': db_score.spelling_score,
                            'vividness_score': db_score.vividness_score,
                            'convention': db_score.convention,
                            'structure_score': db_score.structure_score,
                            'content_score': db_score.content_score,
                            'total_score': db_generation.total_score,
                        }
                    elif locals().get('chain_result'):
                        # Get the result from the chain
                        chain_score_result = [
                            json.loads(result) for result in chain_result.result
                        ]
                        scores_dict = {
                            'grammar_score': chain_score_result[1].get('grammar_score', 0),
                            'spelling_score': chain_score_result[1].get('spelling_score', 0),
                            'vividness_score': chain_score_result[1].get('vividness_score', 0),
                            'convention': chain_score_result[1].get('convention', 0),
                            'structure_score': chain_score_result[1].get('structure_score', 0),
                            'content_score': chain_score_result[1].get('content_score', 0),
                            'total_score': chain_score_result[0].get('total_score', 0),
                        }
                        image_similarity = chain_score_result[1].get('image_similarity', 0)
                    else:
                        raise HTTPException(status_code=500, detail="No score found")
                else:
                    scores_dict = None
                    image_similarity = None

                if not db_generation.is_completed:
                    # initialize start_time for duration calculation
                    start_time = datetime.datetime.now(tz=JST)
                    duration = 0

                    generation_com = schemas.GenerationComplete(
                        id=db_generation.id,
                        is_completed=True
                    )
                    crud.update_generation3(
                        db=db,
                        generation=generation_com
                    )

                    descriptions = crud.get_description(db, leaderboard_id=db_round.leaderboard_id, model_name=db_round.model)
                    descriptions = [des.content for des in descriptions]

                    # Set messages for score and evaluation
                    db_messages = []

                    if "AWS" in db_program.feedback:
                        score_message = """あなたの回答（評価対象）：{user_sentence}

修正された回答　　　　 ：{correct_sentence}


| 　　          | 得点   | 満点       |
|---------------|--------|------|
| 文法得点      |{:>5}|  3  |
| スペリング得点|{:>5}|  1  |
| 鮮明さ        |{:>5}|  1  |
| 自然さ        |{:>5}|  1  |
| 構造性        |{:>5}|  1  |
| 内容得点      |{:>5}|  3  |
| 合計点        |{:>5}| 100 |
| ランク        |{:>5}|(A-最高, B-上手, C-良い, D-普通, E-もう少し, F-頑張ろう)|""".format(
                            round(scores_dict['grammar_score'],2),
                            round(scores_dict['spelling_score'],2),
                            round(scores_dict['vividness_score'],2),
                            scores_dict['convention'],
                            scores_dict['structure_score'],
                            scores_dict['content_score'],
                            scores_dict['total_score'],
                            db_generation.rank,
                            user_sentence=db_generation.sentence,
                            correct_sentence=db_generation.correct_sentence,
                        )

                        db_messages.append(crud.create_message(
                            db=db,
                            message=schemas.MessageBase(
                                content=score_message,
                                sender="assistant",
                                created_at=datetime.datetime.now(tz=JST),
                                is_hint=False,
                                is_evaluation=True,
                            ),
                            chat_id=db_round.chat_history
                        )['message'])

                    if "AWE" in db_program.feedback:
                        evaluation = await asyncio.to_thread(
                            chatbot_obj.get_short_result,
                            db_generation.sentence,
                            db_generation.correct_sentence,
                            db_round.leaderboard.original_image.image,
                            db_generation.grammar_errors,
                            db_generation.spelling_errors,
                            descriptions
                        )
                    else:
                        evaluation = None
                        db_evaluate_msg = None


                    if evaluation:
                        recommended_vocab = ""
                        if len(db_round.generations) > 2:
                            recommended_vocabs = db_round.leaderboard.vocabularies
                            recommended_vocabs = [vocab.word for vocab in recommended_vocabs]
                            if recommended_vocabs:
                                recommended_vocab = "\n\n**おすすめの単語**\n" + ", ".join(recommended_vocabs)

                        evaluation_message = """{feedback}{recommended_vocab}""". \
                        format(
                            feedback=evaluation['feedback'],
                            recommended_vocab=recommended_vocab
                        )

                        db_evaluate_msg = crud.create_message(
                            db=db,
                            message=schemas.MessageBase(
                                content=evaluation_message,
                                sender="assistant",
                                created_at=datetime.datetime.now(tz=JST),
                                is_hint=False,

                                is_evaluation=True,
                                responses_id=chatbot_obj.prev_res_id
                            ),
                            chat_id=db_round.chat_history
                        )['message']

                        db_messages.append(db_evaluate_msg)

                    generation_com = schemas.GenerationComplete(
                        id=db_generation.id,
                        is_completed=True,
                        evaluation_id=db_evaluate_msg.id if db_evaluate_msg else None
                    )

                    db_generation = crud.update_generation3(
                        db=db,
                        generation=generation_com,
                    )

                # prepare data to send
                send_data = {
                    "leaderboard": {
                        "id": leaderboard_id,
                        "image": db_leaderboard.original_image.image,
                    },
                    "round": {
                        "id": db_round.id,
                        "display_name": db_round.display_name,
                        "generated_time":generated_time,
                    },
                    "chat": {
                        "id": db_round.chat_history,
                        "messages" : [
                            {
                                'id': db_message.id,
                                'sender': db_message.sender,
                                'content': db_message.content,
                                'created_at': db_message.created_at.isoformat(),
                                'is_hint': db_message.is_hint
                            }
                            for db_message in db_messages
                        ]
                    },
                    "generation": {
                        "id": db_generation.id,
                        "interpreted_image": db_generation.interpreted_image.image if db_generation.interpreted_image else None,
                        "image_similarity": image_similarity,
                        "evaluation_msg": db_evaluate_msg.content if 'AWE' in db_program.feedback else None
                    }
                }

            # if user requests to end the round
            elif user_action["action"] == "end":
                duration = np.sum([g.duration for g in db_round.generations if g.is_completed])

                db_round = crud.complete_round(
                    db=db,
                    round_id=db_round.id,
                    round=schemas.RoundComplete(
                        id=db_round.id,
                        last_generation_id=db_generation.id,
                        is_completed=True,
                        duration=duration,
                    )
                )

                # prepare data to send
                send_data = {
                    "leaderboard": {
                        "id": leaderboard_id,
                        "image": db_leaderboard.original_image.image,
                    },
                    "round": {
                        "id": db_round.id,
                        "generated_time":generated_time,
                    },
                    "chat": {
                        "id": db_round.chat_history,
                        "messages" : []
                    },
                }

                chatbot_obj.kill()
            else:
                send_data = {}
                logger1.error(f"Unknown action received: {user_action['action']}")
            # send details to the user
            await websocket.send_json(send_data)

            crud.update_user_action(
                db=db,
                user_action=schemas.UserActionUpdate(
                    id=db_user_action.id,
                    related_id=db_generation.id if db_generation else None,
                    sent_at=datetime.datetime.now(tz=JST),
                )
            )

    except WebSocketDisconnect:
        disconnect_time = datetime.datetime.now(tz=JST)

        # record disconnect time
        crud.create_user_action(
            db=db,
            user_action=schemas.UserActionBase(
                user_id=player_id,
                action="disconnect websocket",
                sent_at=disconnect_time,
                received_at=disconnect_time,
            )
        )
        logger1.info(f"WebSocket disconnected for user {player_id}")
    except Exception as e:
        logger1.error(f"Error in websocket: {str(e)}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass
    finally:
        disconnect_time = datetime.datetime.now(tz=JST)
        if start_time and db_generation and not db_generation.is_completed:
            duration += (disconnect_time - start_time).total_seconds()
            crud.update_generation_duration(
                db=db,
                generation_id=db_generation.id,
                duration=duration
            )
