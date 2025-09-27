from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta
from fastapi import HTTPException
from datetime import timezone, datetime
from typing import Union, List, Annotated, Optional

from sql_app_2.dependencies import sentence as sentence2, score as score2, dictionary as dictionary2, gen_image as gen_image2, openai_chatbot as openai_chatbot2
from sql_app_2 import crud as crud2, schemas as schemas2, database as database2
from util import computing_time_tracker , encode_image
from sql_app_2.database import SessionLocal2, engine2

import torch

import os, time, json, io, requests
from celery import Celery
from celery.schedules import crontab

app = Celery(__name__)
app.conf.broker_url = os.environ.get('BROKER_URL',
                                        'redis://localhost:7876')
app.conf.result_backend = os.environ.get('RESULT_BACKEND',
                                            'redis://localhost:7876')

app.conf.timezone = 'Asia/Tokyo'

app.conf.beat_schedule = {
    'check_error_task': {
        'task': 'tasks.check_error_task',
        'schedule': crontab(minute=0, hour=5),
    }
}

class AlchemyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # Convert SQLAlchemy model to dictionary
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    json.dumps(data)
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            return fields
        return json.JSONEncoder.default(self, obj)

# sql_app_2 tasks

@app.task(name='tasks.generateDescription2', ignore_result=False, track_started=True)
def generateDescription2(
    leaderboard_id: int, image: str, story: Optional[str], model_name: str="gpt-4o-mini"
):
    
    try:
        db=SessionLocal2()

        response_id, contents = sentence2.generateSentence(
            base64_image=image,
            story=story
        )

        db_descriptions = []

        for content in contents:
            d = schemas2.DescriptionBase(
                content=content,
                model=model_name,
                leaderboard_id=leaderboard_id
            )
            
            db_description = crud2.create_description(
                db=db,
                description=d
            )
            
            db_descriptions.append(db_description)
        
        db_leaderboard = crud2.update_leaderboard(
            db=db,
            leaderboard=schemas2.LeaderboardUpdateInternal(
                id=leaderboard_id,
                response_id=response_id,
            )
        )
        db_leaderboard = crud2.update_leaderboard_difficulty(
            db=db,
            leaderboard_id=leaderboard_id,
            difficulty_level=len(contents)
        )

        output = json.dumps(db_descriptions, cls=AlchemyEncoder)

        return output
    except Exception as e:
        print(f"Generate description error: {e}")
    finally:
        if db:
            db.close()

@app.task(name='tasks.calculate_score_gpt', ignore_result=False, track_started=True)
def calculate_score_gpt(
    items: tuple,
):
    
    if items is None:
        raise HTTPException(status_code=400, detail="Invalid items")
    if isinstance(items, tuple):
        generation = items[0]
    elif 'id' in items:
        generation = items
    try:
        
        db=SessionLocal2()

        db_generation = crud2.get_generation(db, generation_id=generation['id'])
        if db_generation is None:
            raise HTTPException(status_code=404, detail="Generation not found")
        db_round = crud2.get_round(db, round_id=db_generation.round_id)
        if db_round is None:
            raise HTTPException(status_code=404, detail="Round not found")
        
        cb = openai_chatbot2.Hint_Chatbot(
            model_name=db_round.model,
            first_res_id=db_round.leaderboard.response_id,
        )

        scores = cb.scoring(
            sentence=db_generation.sentence,
            base64_image=db_round.leaderboard.original_image.image,
        )

        if scores is None:
            raise HTTPException(status_code=500, detail="Error calculating score")
        
        db_score = crud2.create_score(
            db=db,
            score=schemas2.ScoreCreate(
                generation_id = db_generation.id,
                grammar_score=scores['grammar'],
                spelling_score=scores['spelling'],
                vividness_score=scores['content_vividness'],
                convention=scores['convention'],
                structure_score=scores['sentence_structure'],
                content_score=scores['content_comprehension'],
            ),
            generation_id=db_generation.id
        )

        
        total_score = db_score.grammar_score + db_score.spelling_score + db_score.vividness_score + db_score.convention + db_score.structure_score
        total_score = int(round(total_score*db_score.content_score)/21*100)
        db_generation = crud2.update_generation3(
            db=db,
            generation=schemas2.GenerationComplete(
                id=db_generation.id,
                total_score=total_score,
                rank=score2.rank(total_score),
                is_completed=False
            )
        )
        if "IMG" in db_round.program.feedback:
            image_similarity = cb.image_similarity(
                image1_base64=db_round.leaderboard.original_image.image,
                image2_base64=db_generation.interpreted_image.image,
            )
        else:
            image_similarity = 0

        db_score = crud2.update_score(
            db=db,
            score=schemas2.ScoreUpdate(
                id=db_score.id,
                image_similarity=image_similarity
            )
        )

        output = [json.dumps(db_generation, cls=AlchemyEncoder),
                 json.dumps(db_score, cls=AlchemyEncoder)]
        return output

    except Exception as e:
        print(f"Calculate score error: {e}")
    finally:
        if db:
            db.close()

@app.task(name='tasks.generate_interpretation2', ignore_result=False)
def generate_interpretation2(
    generation_id: int,
    sentence: str,
    at: datetime, 
):
    
    db=None
    try:
        db=SessionLocal2()

        db_generation = crud2.get_generation(db, generation_id=generation_id)
        if db_generation.interpreted_image_id is not None:
            return {
                'id': db_generation.id,
                'at': at,
            }
        db_leaderboard = crud2.get_leaderboard(db, leaderboard_id=db_generation.round.leaderboard_id)
        t = computing_time_tracker("Generate interpretation")
        try:
            image = gen_image2.generate_interpretion(
                sentence=sentence, 
                model="gemini",
                style=db_leaderboard.scene.prompt
            )
            t.stop_timer()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
        
        # Database operations
        db_interpreted_image = crud2.create_interpreted_image(
            db=db,
            image=schemas2.ImageBase(
                image=image,
            )
        )

        db_generation = crud2.update_generation2(
            db=db,
            generation=schemas2.GenerationInterpretation(
                id=generation_id,
                interpreted_image_id=db_interpreted_image.id,
            )
        )

        return {
            'id': db_generation.id,
            'at': at,
        }
    except Exception as e:
        print(f"Generate interpretation error: {e}")
    finally:
        if db:
            db.close()