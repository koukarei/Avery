from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta
from .dependencies import sentence, score, dictionary, gen_image
from . import crud, schemas, database
from typing import Union, List, Annotated, Optional
from fastapi import HTTPException
from datetime import timezone, datetime
from .dependencies.util import computing_time_tracker, encode_image
from .database import SessionLocal, engine

import torch

import os, time, json, io, requests, asyncio
from celery import Celery, chain, group

app = Celery(__name__)
app.conf.broker_url = os.environ.get('BROKER_URL',
                                        'redis://localhost:7876')
app.conf.result_backend = os.environ.get('RESULT_BACKEND',
                                            'redis://localhost:7876')
nlp_models = {}

def model_load():
    en_nlp = dictionary.Dictionary()
    from transformers import GPT2Tokenizer, GPT2LMHeadModel
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    perplexity_model = GPT2LMHeadModel.from_pretrained("gpt2")
    perplexity_model.eval()
    if torch.cuda.is_available():
        perplexity_model.to('cuda')
    return en_nlp, tokenizer, perplexity_model

nlp_models['en_nlp'], nlp_models['tokenizer'], nlp_models['perplexity_model'] = model_load()

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

@app.task(name='tasks.generateDescription', ignore_result=True)
def generateDescription(leaderboard_id: int, image: str, story: Optional[str], model_name: str="gpt-4o-mini"):
    
    try:
        db=database.SessionLocal()

        contents = sentence.generateSentence(
            base64_image=image,
            story=story
        )

        db_descriptions = []

        for content in contents:
            d = schemas.DescriptionBase(
                content=content,
                model=model_name,
                leaderboard_id=leaderboard_id
            )
            
            db_description = crud.create_description(
                db=db,
                description=d
            )
            
            db_descriptions.append(db_description)
        
        db_leaderboard = crud.update_leaderboard_difficulty(
            db=db,
            leaderboard_id=leaderboard_id,
            difficulty_level=len(contents)
        )

        output = json.dumps(db_descriptions, cls=AlchemyEncoder)

        return output
    except Exception as e:
        print(f"Generate description error: {e}")
    finally:
        db.close()

def check_factors_done(
    generation_id: int,
    delete_tasks: bool=False
):
    try:
        db=database.SessionLocal()

        db_generation = crud.get_generation(db, generation_id=generation_id)
        if db_generation is None:
            raise HTTPException(status_code=404, detail="Generation not found")
        if all([
            db_generation.updated_n_words,
            db_generation.updated_grammar_errors,
            db_generation.updated_perplexity,
            db_generation.updated_content_score
        ]):
            celery_tasks = crud.get_tasks(db, generation_id=generation_id)
            for t in celery_tasks:
                crud.delete_task(db, t.id)
            return {
                "status": "FINISHED",
                "tasks": []
            }

        celery_tasks = crud.get_tasks(db, generation_id=generation_id)
        output = []
        for t in celery_tasks:
            result = app.AsyncResult(t.id)
            output.append(
                schemas.TaskStatus(
                    id=t.id,
                    status=result.status,
                    result=result.result
                )
            )
            if result.status == "SUCCESS":
                crud.delete_task(db, t.id)
            elif delete_tasks:
                app.control.revoke(t.id, terminate=True)
                crud.delete_task(db, t.id)
        
        return {
            "status": "PENDING",
            "tasks": output
        }
    except Exception as e:
        print(f"Check factors done error: {e}")
    finally:
        db.close()

@app.task(name="tasks.check_factors_done_by_dict")
def check_factors_done_by_dict(
    generation: dict,
):
    try:
        db=database.SessionLocal()
        generation_id = generation['id']
        db_generation = crud.get_generation(db, generation_id=generation_id)
        if db_generation is None:
            raise HTTPException(status_code=404, detail="Generation not found")
        if all([
            db_generation.updated_n_words,
            db_generation.updated_grammar_errors,
            db_generation.updated_perplexity,
            db_generation.updated_content_score
        ]):
            celery_tasks = crud.get_tasks(db, generation_id=generation_id)
            for t in celery_tasks:
                crud.delete_task(db, t.id)
            return {
                "status": "FINISHED",
                "tasks": []
            }

        celery_tasks = crud.get_tasks(db, generation_id=generation_id)
        output = []
        for t in celery_tasks:
            result = app.AsyncResult(t.id)
            output.append(
                schemas.TaskStatus(
                    id=t.id,
                    status=result.status,
                    result=result.result
                )
            )
            if result.status == "SUCCESS":
                crud.delete_task(db, t.id)
        
        return {
            "status": "PENDING",
            "tasks": output
        }
    except Exception as e:
        print(f"Check factors done error: {e}")
    finally:
        db.close()

def calculate_score(
    db: Session,
    generation: schemas.GenerationCompleteCreate,
    is_completed: bool=False, 
):
    try:
        db_generation = crud.get_generation(db, generation_id=generation.id)
        if db_generation is None:
            raise HTTPException(status_code=404, detail="Generation not found")
        db_round = crud.get_round(db, round_id=db_generation.round_id)

        if is_completed:
            generation_aware = generation.at.replace(tzinfo=timezone.utc)
            db_generation_aware = db_round.created_at.replace(tzinfo=timezone.utc)
            duration = (generation_aware - db_generation_aware).seconds
        else: 
            duration = 0

        factors = {
            'n_words': db_generation.n_words,
            'n_conjunctions': db_generation.n_conjunctions,
            'n_adj': db_generation.n_adj,
            'n_adv': db_generation.n_adv,
            'n_pronouns': db_generation.n_pronouns,
            'n_prepositions': db_generation.n_prepositions,
            'n_grammar_errors': db_generation.n_grammar_errors,
            'grammar_errors': db_generation.grammar_errors,
            'n_spelling_errors': db_generation.n_spelling_errors,
            'spelling_errors': db_generation.spelling_errors,
            'perplexity': db_generation.perplexity,
            'f_word': db_generation.f_word,
            'f_bigram': db_generation.f_bigram,
            'n_clauses': db_generation.n_clauses,
            'content_score': db_generation.content_score
        }

        try:
            scores = score.calculate_score(**factors)
        except Exception as e:
            print(f"Calculate score error: {e}")
            print(f"Factors: {factors}")
            raise HTTPException(status_code=500, detail="Error calculating score")

        generation_com = schemas.GenerationComplete(
            id=db_generation.id,
            total_score=scores['total_score'],
            rank=score.rank(scores['total_score']),
            duration=duration,
            is_completed=is_completed
        )
        
        crud.update_generation3(
            db=db,
            generation=generation_com
        )

        return factors, scores
    except Exception as e:
        print(f"Calculate score error: {e}")

@app.task(name='tasks.update_vocab_used_time', ignore_result=True)
def update_vocab_used_time(
        sentence: str,
        user_id: int,
):
    try:
        db=database.SessionLocal()
        updated_vocab = []
        doc = nlp_models['en_nlp'].get_sentence_nlp(sentence)
        for token in doc:
            db_vocab = crud.get_vocabulary(
                db=db,
                vocabulary=token.lemma,
                part_of_speech=token.pos
            )
            if db_vocab:
                db_personal_dictionary = crud.get_personal_dictionary(
                    db=db,
                    player_id=user_id,
                    vocabulary_id=db_vocab.id
                )

                if db_personal_dictionary:
                    updated_vocab.append(
                        crud.update_personal_dictionary_used(
                            db=db,
                            dictionary=schemas.PersonalDictionaryId(
                                player=user_id,
                                vocabulary=db_vocab
                            )
                        )
                    )

        output = [
            json.dumps(db_vocab, cls=AlchemyEncoder)
            for db_vocab in updated_vocab
        ]
        return output
    except Exception as e:
        print(f"Update vocab used time error: {e}")
    finally:
        db.close()

@app.task(name='tasks.update_n_words', ignore_result=True)
def update_n_words(
    generation: dict,
):
    try:
        generation = schemas.GenerationCompleteCreate(**generation)
        en_nlp = nlp_models['en_nlp'].en_nlp
        db=database.SessionLocal()
        db_generation = crud.get_generation(db, generation_id=generation.id)
        if db_generation.updated_n_words:
            return json.dumps(db_generation, cls=AlchemyEncoder)

        t = computing_time_tracker("Update n_words")
        doc = en_nlp(db_generation.sentence)
        words=[w for s in doc.sentences for w in s.words]
        factors=score.n_wordsNclauses(
            doc=doc,
            words=words
        )

        db_generation = crud.update_generation3(
            db=db,
            generation=schemas.GenerationComplete(
                id=db_generation.id,
                n_words=factors['n_words'],
                n_conjunctions=factors['n_conjunctions'],
                n_adj=factors['n_adj'],
                n_adv=factors['n_adv'],
                n_pronouns=factors['n_pronouns'],
                n_prepositions=factors['n_prepositions'],
                n_clauses=factors['n_clauses'],
                is_completed=False,
                updated_n_words=True
            )
        )
        t.stop_timer()

        output = json.dumps(db_generation, cls=AlchemyEncoder)
        return output
    except Exception as e:
        print(f"Update n_words error: {e}")
    finally:
        db.close()

@app.task(name='tasks.update_grammar_spelling', ignore_result=True)
def update_grammar_spelling(
    generation: dict,
):
    try:
        generation = schemas.GenerationCompleteCreate(**generation)
        en_nlp = nlp_models['en_nlp'].en_nlp
        db=database.SessionLocal()
        db_generation = crud.get_generation(db, generation_id=generation.id)
        if db_generation.updated_grammar_errors:
            return json.dumps(db_generation, cls=AlchemyEncoder)
        
        t = computing_time_tracker("Update grammar spelling")

        factors = score.grammar_spelling_errors(db_generation.sentence, en_nlp=en_nlp)

        db_generation = crud.update_generation3(
            db=db,
            generation=schemas.GenerationComplete(
                id=db_generation.id,
                grammar_errors=str(factors['grammar_error']),
                spelling_errors=str(factors['spelling_error']),
                n_grammar_errors=factors['n_grammar_errors'],
                n_spelling_errors=factors['n_spelling_errors'],
                is_completed=False,
                updated_grammar_errors=True
            )
        )
        t.stop_timer()

        output = json.dumps(db_generation, cls=AlchemyEncoder)
        return output
    except Exception as e:
        print(f"Update grammar spelling error: {e}")
    finally:
        db.close()

@app.task(name='tasks.update_frequency_word', ignore_result=True)
def update_frequency_word(
    generation: dict,
):
    try:
        generation = schemas.GenerationCompleteCreate(**generation)
        en_nlp = nlp_models['en_nlp'].en_nlp
        db=database.SessionLocal()
        db_generation = crud.get_generation(db, generation_id=generation.id)
        if db_generation.updated_f_word:
            return json.dumps(db_generation, cls=AlchemyEncoder)

        t = computing_time_tracker("Update frequency word")
        doc = en_nlp(db_generation.sentence)
        words=[w for s in doc.sentences for w in s.words]

        factors = score.frequency_score(words=words)

        db_generation = crud.update_generation3(
            db=db,
            generation=schemas.GenerationComplete(
                id=db_generation.id,
                f_word=factors['f_word'],
                f_bigram=factors['f_bigram'],
                is_completed=False,
                updated_f_word=True
            )
        )

        t.stop_timer()

        output = json.dumps(db_generation, cls=AlchemyEncoder)
        return output
    except Exception as e:
        print(f"Update frequency word error: {e}")
    finally:
        db.close()

@app.task(name='tasks.update_perplexity', ignore_result=True)
def update_perplexity(
        generation: dict,
        descriptions: list[str]
):
    try:
        generation = schemas.GenerationCompleteCreate(**generation)
        db=database.SessionLocal()

        db_generation = crud.get_generation(db, generation_id=generation.id)
        if db_generation.updated_perplexity:
            return json.dumps(db_generation, cls=AlchemyEncoder)
        
        db_round = crud.get_round(db, round_id=db_generation.round_id)

        descriptions =  crud.get_description(db, leaderboard_id=db_round.leaderboard_id, model_name=db_round.model)
        descriptions = [des.content for des in descriptions]   

        en_nlp = nlp_models['en_nlp'].en_nlp
        perplexity_model = nlp_models['perplexity_model']
        tokenizer = nlp_models['tokenizer']

        t = computing_time_tracker("Update perplexity")
        db_generation = crud.get_generation(db, generation_id=generation.id)
        doc = en_nlp(db_generation.sentence)
        words=[w for s in doc.sentences for w in s.words]
        
        cut_points=[w.end_char+1 for w in words if w.start_char != 0]
        
        factors = score.perplexity(
            perplexity_model=perplexity_model,
            tokenizer=tokenizer,
            sentence=db_generation.sentence,
            cut_points=cut_points,
            descriptions=descriptions
        )

        db_generation = crud.update_generation3(
            db=db,
            generation=schemas.GenerationComplete(
                id=db_generation.id,
                perplexity=factors['perplexity'],
                is_completed=False,
                updated_perplexity=True
            )
        )

        t.stop_timer()

        output = json.dumps(db_generation, cls=AlchemyEncoder)
        return output
    except Exception as e:
        print(f"Update perplexity error: {e}")
    finally:
        db.close()

@app.task(name='tasks.update_content_score', ignore_result=True)
def update_content_score(
    generation: dict,
):
    try:
        generation = schemas.GenerationCompleteCreate(**generation)
        db=database.SessionLocal()
        db_generation = crud.get_generation(db, generation_id=generation.id)
        if db_generation.updated_content_score:
            return json.dumps(db_generation, cls=AlchemyEncoder)
        t = computing_time_tracker("Update content score")


        db_round = crud.get_round(db, round_id=db_generation.round_id)

        factors = score.calculate_content_score_celery(
            image=db_round.leaderboard.original_image.image,
            sentence=db_generation.sentence
        )

        db_generation = crud.update_generation3(
            db=db,
            generation=schemas.GenerationComplete(
                id=db_generation.id,
                content_score=factors['content_score'],
                is_completed=False,
                updated_content_score=True
            )
        )
        t.stop_timer()

        output = json.dumps(db_generation, cls=AlchemyEncoder)
        return output
    except Exception as e:
        print(f"Update content score error: {e}")
    finally:
        db.close()

@app.task(name='tasks.generate_interpretation')
def generate_interpretation(
    generation_id: int,
    sentence: str,
    at: str
):
    try:
        db=database.SessionLocal()
        t = computing_time_tracker("Generate interpretation")
        url = gen_image.generate_interpretion(sentence)
        t.stop_timer()

        # Download and save image
        try:
            b_interpreted_image = io.BytesIO(requests.get(url).content)
            image = encode_image(image_file=b_interpreted_image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
        
        # Database operations
        db_interpreted_image = crud.create_interpreted_image(
            db=db,
            image=schemas.ImageBase(
                image=image,
            )
        )

        db_generation = crud.update_generation2(
            db=db,
            generation=schemas.GenerationInterpretation(
                id=generation_id,
                interpreted_image_id=db_interpreted_image.id,
            )
        )

        at = datetime.strptime(at, "%Y-%m-%d %H:%M:%S")

        generation_complete = schemas.GenerationCompleteCreate(
            id=db_generation.id,
            at=at
        )

        return generation_complete.model_dump()
    except Exception as e:
        print(f"Generate interpretation error: {e}")
    finally:
        db.close()

@app.task(name='tasks.image_similarity', ignore_result=True)
def image_similarity(
    generation: dict
):
    try:
        generation_id = generation['id']
        db=database.SessionLocal()
        t = computing_time_tracker("Image similarity")
        
        db_generation = crud.get_generation(
            db=db,
            generation_id=generation_id
        )

        db_round = crud.get_round(
            db=db,
            round_id=db_generation.round_id
        )

        # if current_user.id != db_round.player_id and not current_user.is_admin:
        #     raise HTTPException(status_code=401, detail="You are not authorized to view images")

        db_leaderboard = crud.get_leaderboard(
            db=db,
            leaderboard_id=db_round.leaderboard_id
        )

        semantic1 = score.calculate_content_score_celery(
            image=db_leaderboard.original_image.image,
            sentence=db_generation.sentence
        )

        semantic2 = score.calculate_content_score_celery(
            image=db_generation.interpreted_image.image,
            sentence=db_generation.sentence
        )

        denominator = semantic1['content_score']+semantic2['content_score']
        if denominator == 0:
            blip2_score = 0
        else:
            blip2_score = abs(semantic1['content_score'] - semantic2['content_score'])/(semantic1['content_score']+semantic2['content_score'])
            blip2_score = 1 - blip2_score

        ssim = score.image_similarity(
            image1=db_leaderboard.original_image.image,
            image2=db_generation.interpreted_image.image
        )["ssim_score"]

        similarity = blip2_score*0.8 + ssim*0.2

        image_similarity = schemas.ImageSimilarity(
            semantic_score_original=semantic1['content_score'],
            semantic_score_interpreted=semantic2['content_score'],
            blip2_score=blip2_score,
            ssim=ssim,
            similarity=similarity

        )

        score_id = db_generation.score_id
        if score_id is not None:
            crud.update_score(
                db=db,
                score=schemas.ScoreUpdate(
                    id=score_id,
                    image_similarity=similarity
                )
            )

        t.stop_timer()
        return image_similarity
    except Exception as e:
        print(f"Image similarity error: {e}")
    finally:
        db.close()
