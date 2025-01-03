from sqlalchemy.orm import Session
from .dependencies import sentence, score, dictionary
from . import crud, schemas
from typing import Union, List, Annotated, Optional
from fastapi import HTTPException
from datetime import timezone
from .dependencies.util import computing_time_tracker

def generateDescription(db: Session, leaderboard_id: int, image: str, story: Optional[str], model_name: str="gpt-4o-mini"):
    
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

    return db_descriptions

def check_factors_done(
    db: Session,
    en_nlp,
    perplexity_model,
    tokenizer,
    generation: schemas.GenerationCompleteCreate,
    descriptions: list
):
    db_generation = crud.get_generation(db, generation_id=generation.id)

    if db_generation.total_score==0:
        if (not db_generation.n_words) or (not db_generation.n_clauses):
            update_n_words(db=db, en_nlp=en_nlp, generation=generation)
        # if (not db_generation.f_word) or (not db_generation.f_bigram):
        #     update_frequency_word(db=db, en_nlp=en_nlp, generation=generation)
        if not db_generation.perplexity:
            update_perplexity(db=db, en_nlp=en_nlp, perplexity_model=perplexity_model, tokenizer=tokenizer, generation=generation, descriptions=descriptions)
        if not db_generation.content_score:
            update_content_score(db=db, generation=generation)
        
    return


def calculate_score(
    db: Session,
    en_nlp,
    perplexity_model,
    tokenizer,
    generation: schemas.GenerationCompleteCreate,
    is_completed: bool=False, 
):
    
    db_generation = crud.get_generation(db, generation_id=generation.id)
    if db_generation is None:
        raise HTTPException(status_code=404, detail="Generation not found")
    db_round = crud.get_round(db, round_id=db_generation.round_id)
    ai_play = crud.get_description(db, leaderboard_id=db_round.leaderboard_id, model_name=db_round.model)

    if not ai_play:
        if db_round.leaderboard.story:
            story=db_round.leaderboard.story.content
        elif db_round.leaderboard.story_extract:
            story=db_round.leaderboard.story_extract
        else:
            story=None
        
        ai_play = generateDescription(
            db=db,
            leaderboard_id=db_round.leaderboard_id, 
            image=str(db_round.leaderboard.original_image.image), 
            story=story, 
            model_name="gpt-4o-mini"
        )
    
    descriptions = [d.content for d in ai_play]

    check_factors_done(
        db=db,
        en_nlp=en_nlp,
        perplexity_model=perplexity_model,
        tokenizer=tokenizer,
        generation=generation, 
        descriptions=descriptions
    )

    if is_completed:
        generation_aware = generation.at.replace(tzinfo=timezone.utc)
        db_generation_aware = db_round.created_at.replace(tzinfo=timezone.utc)
        duration = (generation_aware - db_generation_aware).seconds
    else: 
        duration = 0

    grammar_spelling = score.grammar_spelling_errors(db_generation.sentence, en_nlp=en_nlp)

    factors = {
        'n_words': db_generation.n_words,
        'n_conjunctions': db_generation.n_conjunctions,
        'n_adj': db_generation.n_adj,
        'n_adv': db_generation.n_adv,
        'n_pronouns': db_generation.n_pronouns,
        'n_prepositions': db_generation.n_prepositions,
        'n_grammar_errors': grammar_spelling['n_grammar_errors'],
        'grammar_errors': grammar_spelling['grammar_error'],
        'n_spelling_errors': grammar_spelling['n_spelling_errors'],
        'spelling_errors': grammar_spelling['spelling_error'],
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
        n_grammar_errors=grammar_spelling['n_grammar_errors'],
        n_spelling_errors=grammar_spelling['n_spelling_errors'],
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

def update_n_words(
    db: Session,
    en_nlp,
    generation: schemas.GenerationCompleteCreate,
):
   t = computing_time_tracker("Update n_words")
   db_generation = crud.get_generation(db, generation_id=generation.id)

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
        is_completed=False
       )
   )
   t.stop_timer()
   return

def update_grammar_spelling(
        db: Session,
        generation: schemas.GenerationCompleteCreate,
        en_nlp
):
    t = computing_time_tracker("Update grammar spelling")
    db_generation = crud.get_generation(db, generation_id=generation.id)

    factors = score.grammar_spelling_errors(db_generation.sentence, en_nlp=en_nlp)

    db_generation = crud.update_generation3(
        db=db,
        generation=schemas.GenerationComplete(
            id=db_generation.id,
            n_grammar_errors=factors['n_grammar_errors'],
            n_spelling_errors=factors['n_spelling_errors'],
            is_completed=False
        )
    )
    t.stop_timer()
    return

def update_frequency_word(
        db: Session,
        en_nlp,
        generation: schemas.GenerationCompleteCreate,
):
    t = computing_time_tracker("Update frequency word")
    db_generation = crud.get_generation(db, generation_id=generation.id)

    doc = en_nlp(db_generation.sentence)
    words=[w for s in doc.sentences for w in s.words]
    factors = score.frequency_score(words=words)

    db_generation = crud.update_generation3(
        db=db,
        generation=schemas.GenerationComplete(
            id=db_generation.id,
            f_word=factors['f_word'],
            f_bigram=factors['f_bigram'],
            is_completed=False
        )
    )

    t.stop_timer()
    return

def update_perplexity(
        db: Session,
        en_nlp,
        perplexity_model,
        tokenizer,
        generation: schemas.GenerationCompleteCreate,
        descriptions: list
):
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
            is_completed=False
        )
    )

    t.stop_timer()
    return

def update_content_score(
    db: Session,
    generation: schemas.GenerationCompleteCreate,
):
    t = computing_time_tracker("Update content score")

    db_generation = crud.get_generation(db, generation_id=generation.id)

    db_round = crud.get_round(db, round_id=db_generation.round_id)

    factors = score.calculate_content_score(
        image=db_round.leaderboard.original_image.image,
        sentence=db_generation.sentence
    )

    db_generation = crud.update_generation3(
        db=db,
        generation=schemas.GenerationComplete(
            id=db_generation.id,
            content_score=factors['content_score'],
            is_completed=False
        )
    )
    t.stop_timer()
    return
