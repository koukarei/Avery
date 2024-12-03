from sqlalchemy.orm import Session
from .dependencies import sentence, score, dictionary
from . import crud, schemas
from pathlib import Path
from typing import Union, List, Annotated, Optional
from fastapi import HTTPException
from datetime import timezone

def generateDescription(db: Session, leaderboard_id: int, image: str, story: Optional[str], model_name: str="gpt-4o-mini"):
    
    contents = sentence.genSentences(
        image=image,
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

    return db_descriptions

def calculate_score(
    db: Session,
    en_nlp,
    perplexity_model,
    tokenizer,
    generation: schemas.GenerationCompleteCreate,
    is_completed: bool=False
):
    
    db_generation = crud.get_generation(db, generation_id=generation.id)
    if db_generation is None:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    if db_generation.duration==0 or db_generation.total_score==0:
        db_round = crud.get_round(db, round_id=db_generation.round_id)
        ai_play = crud.get_description(db, leaderboard_id=db_round.leaderboard_id, model_name=db_round.model)

        if not ai_play:
            story_path=db_round.leaderboard.story.textfile_path
            story=Path(story_path).read_text()
            
            ai_play = generateDescription(
                db=db,
                leaderboard_id=db_round.leaderboard_id, 
                image=str(db_round.leaderboard.original_image.image_path), 
                story=story, 
                model_name="gpt-4o-mini"
            )


        if is_completed:
            generation_aware = generation.at.replace(tzinfo=timezone.utc)
            db_generation_aware = db_generation.created_at.replace(tzinfo=timezone.utc)
            duration = (generation_aware - db_generation_aware).seconds
        else: 
            duration = 0

        factors, scores=score.calculate_score_init(
            en_nlp=en_nlp,
            perplexity_model=perplexity_model,
            tokenizer=tokenizer,
            image_path=db_round.leaderboard.original_image.image_path,
            sentence=db_generation.sentence,
        )


        generation_com = schemas.GenerationComplete(
            id=db_round.id,
            n_words=factors['n_words'],
            n_conjunctions=factors['n_conjunctions'],
            n_adj=factors['n_adj'],
            n_adv=factors['n_adv'],
            n_pronouns=factors['n_pronouns'],
            n_prepositions=factors['n_prepositions'],

            n_grammar_errors=factors['n_grammar_errors'],
            n_spelling_errors=factors['n_spelling_errors'],

            perplexity=factors['perplexity'],

            f_word=factors['f_word'],
            f_bigram=factors['f_bigram'],

            n_clauses=factors['n_clauses'],

            content_score=scores['content_score'],

            total_score=scores['total_score'],
            rank=score.rank(scores['total_score']),
            duration=duration,
            is_completed=is_completed
        )

    else:

        generation_aware = generation.at.replace(tzinfo=timezone.utc)
        db_generation_aware = db_generation.created_at.replace(tzinfo=timezone.utc)
        duration = (generation_aware - db_generation_aware).seconds

        generation_com = schemas.GenerationComplete(
            id=db_generation.id,
            
            n_words=db_generation.n_words,
            n_conjunctions=db_generation.n_conjunctions,
            n_adj=db_generation.n_adj,
            n_adv=db_generation.n_adv,
            n_pronouns=db_generation.n_pronouns,
            n_prepositions=db_generation.n_prepositions,

            n_grammar_errors=db_generation.n_grammar_errors,
            n_spelling_errors=db_generation.n_spelling_errors,

            perplexity=db_generation.perplexity,

            f_word=db_generation.f_word,
            f_bigram=db_generation.f_bigram,

            n_clauses=db_generation.n_clauses,

            content_score=db_generation.content_score,

            total_score=db_generation.total_score,
            rank=db_generation.rank,
            duration=duration,
            is_completed=is_completed
        )

        factors = {
            'n_words': db_generation.n_words,
            'n_conjunctions': db_generation.n_conjunctions,
            'n_adj': db_generation.n_adj,
            'n_adv': db_generation.n_adv,
            'n_pronouns': db_generation.n_pronouns,
            'n_prepositions': db_generation.n_prepositions,
            'n_grammar_errors': db_generation.n_grammar_errors,
            'n_spelling_errors': db_generation.n_spelling_errors,
            'perplexity': db_generation.perplexity,
            'f_word': db_generation.f_word,
            'f_bigram': db_generation.f_bigram,
            'n_clauses': db_generation.n_clauses,
            'content_score': db_generation.content_score
        }
        
        scores = score.calculate_score(**factors)

    crud.update_generation3(
        db=db,
        generation=generation_com
    )

    return factors, scores

def update_vocab_used_time(
        db: Session,
        sentence: str,
        user_id: int,
):
    updated_vocab = []
    doc = dictionary.get_sentence_nlp(sentence)
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
    return updated_vocab