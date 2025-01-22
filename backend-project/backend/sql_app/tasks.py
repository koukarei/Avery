from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta
from .dependencies import sentence, score, dictionary, gen_image, openai_chatbot
from . import crud, schemas, database
from typing import Union, List, Annotated, Optional
from fastapi import HTTPException
from datetime import timezone, datetime
from .dependencies.util import computing_time_tracker, encode_image
from .database import SessionLocal, engine

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
        if db:
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

@app.task(name="tasks.check_factors_done_by_dict")
def check_factors_done_by_dict(
    items: tuple,
):
    if items is None:
        raise HTTPException(status_code=400, detail="Invalid items")
    generation = items[0]
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
                "id": generation_id,
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
            "id": generation_id,
            "status": "PENDING",
            "tasks": output
        }
    except Exception as e:
        print(f"Check factors done error: {e}")
    finally:
        if db:
            db.close()

@app.task(name='tasks.pass_generation_dict')
def pass_generation_dict(
    generation: tuple,
):
    if generation is None:
        raise HTTPException(status_code=400, detail="Invalid generation: None type")
    if 'id' in generation:
        return generation
    return generation[0]

@app.task(name='tasks.calculate_score', ignore_result=True)
def calculate_score(
    generation: dict,
    is_completed: bool=False, 
):
    try:
        db=database.SessionLocal()
        generation_id = generation['id']
        db_generation = crud.get_generation(db, generation_id=generation_id)
        if db_generation is None:
            raise HTTPException(status_code=404, detail="Generation not found")
        db_round = crud.get_round(db, round_id=db_generation.round_id)

        if is_completed:
            generation_aware = generation['at'].replace(tzinfo=timezone.utc)
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

        if db_generation.score_id is not None:
            db_scores = crud.get_score(db, score_id=db_generation.score_id)
            scores = json.dumps(db_scores, cls=AlchemyEncoder)
            scores = json.loads(scores)
            scores['total_score'] = db_generation.total_score
            if is_completed and not db_generation.is_completed:
                generation_com = schemas.GenerationComplete(
                    id=db_generation.id,
                    duration=duration,
                    is_completed=is_completed
                )
                crud.update_generation3(
                    db=db,
                    generation=generation_com
                )
            return factors, scores

        try:
            scores = score.calculate_score(**factors)
        except Exception as e:
            print(f"Calculate score error: {e}")
            print(f"Factors: {factors}")
            raise HTTPException(status_code=500, detail="Error calculating score")

        crud.create_score(
            db=db,
            score=schemas.ScoreCreate(
                generation_id=generation_id,
                grammar_score=scores['grammar_score'],
                spelling_score=scores['spelling_score'],
                vividness_score=scores['vividness_score'],
                convention=scores['convention'],
                structure_score=scores['structure_score'],
                content_score=scores['content_score'],
            ),
            generation_id=generation_id
        )

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
    finally:
        if db:
            db.close()

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
        if db:
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
        if db:
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
        if db:
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
        if db:
            db.close()

@app.task(name='tasks.update_perplexity', ignore_result=True)
def update_perplexity(
        generation: dict
):
    db=None
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
        if db:
            db.close()

@app.task(name='tasks.update_content_score', ignore_result=True)
def update_content_score(
    generation: dict,
):
    try:
        print("update content score", generation)
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
        if db:
            db.close()

@app.task(name='tasks.generate_interpretation', ignore_result=False)
def generate_interpretation(
    generation_id: int,
    sentence: str,
    at: datetime
):
    db=None
    try:
        db=database.SessionLocal()
        db_generation = crud.get_generation(db, generation_id=generation_id)
        if db_generation.interpreted_image_id is not None:
            return {
                'id': db_generation.id,
                'at': at,
            }
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

        return {
            'id': db_generation.id,
            'at': at,
        }
    except Exception as e:
        print(f"Generate interpretation error: {e}")
    finally:
        if db:
            db.close()

@app.task(name='tasks.image_similarity', ignore_result=True)
def cal_image_similarity(
    generation: tuple
):
    if generation is None:
        raise HTTPException(status_code=400, detail="Invalid generation: None type")
    generation = generation[0]        
    try:
        generation_id = generation['id']
        db=database.SessionLocal()
        t = computing_time_tracker("Image similarity")
        
        db_generation = crud.get_generation(
            db=db,
            generation_id=generation_id
        )

        if db_generation.score_id is not None:
            if db_generation.score.image_similarity:
                return db_generation.score.image_similarity

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

        semantic1 = db_generation.content_score

        semantic2 = score.calculate_content_score_celery(
            image=db_generation.interpreted_image.image,
            sentence=db_generation.sentence
        )

        denominator = semantic1+semantic2['content_score']
        if denominator == 0:
            blip2_score = 0
        else:
            blip2_score = abs(semantic1 - semantic2['content_score'])/(semantic1+semantic2['content_score'])
            blip2_score = 1 - blip2_score

        ssim = score.image_similarity(
            image1=db_leaderboard.original_image.image,
            image2=db_generation.interpreted_image.image
        )["ssim_score"]

        similarity = blip2_score*0.8 + ssim*0.2

        image_similarity = schemas.ImageSimilarity(
            semantic_score_original=semantic1,
            semantic_score_interpreted=semantic2['content_score'],
            blip2_score=blip2_score,
            ssim=ssim,
            similarity=similarity

        )

        score_id = db_generation.score_id
        if score_id is None:
            raise HTTPException(status_code=404, detail="Score not found")
        crud.update_score(
            db=db,
            score=schemas.ScoreUpdate(
                id=score_id,
                image_similarity=similarity
            )
        )

        t.stop_timer()
        return image_similarity.model_dump()
    except Exception as e:
        print(f"Image similarity error: {e}")
    finally:
        if db:
            db.close()

@app.task(name="tasks.complete_generation_backend", ignore_result=True)
def complete_generation_backend(
    items: tuple,
):
    if items is None:
        raise HTTPException(status_code=400, detail="Invalid generation: None type")
    generation = items[0]        
    
    try:
        generation_id = generation['id']
        db=database.SessionLocal()
        t = computing_time_tracker("Complete generation")

        db_generation = crud.get_generation(
            db=db,
            generation_id=generation_id
        )

        if db_generation.is_completed:
            return generation

        db_round = crud.get_round(
            db=db,
            round_id=db_generation.round_id
        )

        db_chat = crud.get_chat(db=db,chat_id=db_round.chat_history)
        
        cb=openai_chatbot.Hint_Chatbot()
        
        factors, scores_dict = items[1]

        descriptions = crud.get_description(db, leaderboard_id=db_round.leaderboard_id, model_name=db_round.model)
        descriptions = [des.content for des in descriptions]

        evaluation = cb.get_result(
            sentence=db_generation.sentence,
            correct_sentence=db_generation.correct_sentence,
            scoring=scores_dict,
            rank=db_generation.rank,
            base64_image=db_round.leaderboard.original_image.image,
            chat_history=db_chat.messages,
            grammar_errors=db_generation.grammar_errors,
            spelling_errors=db_generation.spelling_errors,
            descriptions=descriptions
        )

        if evaluation:
            score_message = """あなたの回答（評価対象）：{user_sentence}

修正された回答　　　　 ：{correct_sentence}


| 　　          | 得点   | 満点       |
|---------------|--------|------|
| 文法得点      |{:>5}|  5  |
| スペリング得点|{:>5}|  5  |
| 鮮明さ        |{:>5}|  5  |
| 自然さ        |{:>5}|  1  |
| 構造性        |{:>5}|  3  |
| 内容得点      |{:>5}| 100 |
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

            if len(db_round.generations) > 2:
                recommended_vocabs = db_round.leaderboard.vocabularies
                recommended_vocabs = [vocab.word for vocab in recommended_vocabs]
                recommended_vocab = "\n\n**おすすめの単語**\n" + ", ".join(recommended_vocabs)
            else:
                recommended_vocab = ""

            evaluation_message = """**文法**
{grammar_feedback}
**スペル**
{spelling_feedback}
**スタイル**
{style_feedback}
**内容**
{content_feedback}

**総合評価**
{overall_feedback}{recommended_vocab}""". \
            format(
                grammar_feedback=evaluation.grammar_evaluation,
                spelling_feedback=evaluation.spelling_evaluation,
                style_feedback=evaluation.style_evaluation,
                content_feedback=evaluation.content_evaluation,
                overall_feedback=evaluation.overall_evaluation,
                recommended_vocab=recommended_vocab
            )

            crud.create_message(
                db=db,
                message=schemas.MessageBase(
                    content=score_message,
                    sender="assistant",
                    created_at=datetime.now(tz=timezone.utc)
                ),
                chat_id=db_round.chat_history
            )

            crud.create_message(
                db=db,
                message=schemas.MessageBase(
                    content=evaluation_message,
                    sender="assistant",
                    created_at=datetime.now(tz=timezone.utc)
                ),
                chat_id=db_round.chat_history
            )

            generation_com = schemas.GenerationComplete(
                id=db_generation.id,
                is_completed=True
            )

            crud.update_generation3(
                db=db,
                generation=generation_com
            )
            return generation_com.model_dump()
        raise HTTPException(status_code=500, detail="Error completing generation")
    except Exception as e:
        print(f"Complete generation error: {e}")
    finally:
        if db:
            db.close()

@app.task(name='tasks.check_error_task', ignore_result=True)
def check_error_task():
    try:
        db=database.SessionLocal()
        # stop at generating images
        generations = crud.get_error_task(
            db=db,
            group_type='no_image'
        )
        if generations:
            for generation in generations:
                generate_interpretation(
                    generation_id=generation.id,
                    sentence=generation.sentence,
                    at=generation.at
                )

        # stop at content score
        generations = crud.get_error_task(
            db=db,
            group_type = 'no_content_score'
        )
        if generations:
            for generation in generations:
                update_content_score(
                    generation={
                        "id": generation.id,
                        "at": datetime.now()
                    }
                )
         
        # stop at word num
        generations = crud.get_error_task(
            db=db,
            group_type='no_word_num'
        )
        if generations:
            for generation in generations:
                update_n_words(
                    generation={
                        "id": generation.id,
                        "at": datetime.now()
                    }
                )
        
        # stop at grammar and spelling
        generations = crud.get_error_task(
            db=db,
            group_type='no_grammar'
        )
        if generations:
            for generation in generations:
                update_grammar_spelling(
                    generation={
                        "id": generation.id,
                        "at": datetime.now()
                    }
                )

        # stop at perplexity
        generations = crud.get_error_task(
            db=db,
            group_type='no_perplexity'
        )
        if generations:
            for generation in generations:
                update_perplexity(
                    generation={
                        "id": generation.id,
                        "at": datetime.now()
                    }
                )

        # stop at calculate total score
        generations = crud.get_error_task(
            db=db,
            group_type='no_score'
        )
        if generations:
            for generation in generations:
                info={
                        "id": generation.id,
                        "at": datetime.now()
                }
                factor_score = calculate_score(
                    generation=info
                )
                complete_generation_backend(
                    items=(
                        info,
                        factor_score
                    )
                )

        # stop at image similarity
        score = crud.get_error_task(
            db=db,
            group_type='no_similarity'
        )
        if score:
            for s in score:
                cal_image_similarity(
                    generation=[{
                        "id": s.generation_id,
                    }]
                )

        # generation complete
        generations = crud.get_error_task(
            db=db,
            group_type='no_complete'
        )

    except Exception as e:
        print(f"Check error task error: {e}")
    finally:
        if db:
            db.close()