# factories.py
import factory
from sqlalchemy.orm import sessionmaker
from .models import *
from .database import engine
import csv
import random

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_files_by_dir(dir_path):
    import os
    files = []
    for r, d, f in os.walk(dir_path):
        for file in f:
            if '.jpg' in file or '.png' in file:
                files.append(os.path.join(r, file))
    return files

public_image_paths=get_files_by_dir('static/Public picture')
interpreted_image_paths=get_files_by_dir('static/Interpreted picture')

class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = SessionLocal()

    id = factory.Sequence(lambda n: n)
    name = factory.Faker('name')
    email = factory.Faker('email')
    display_name = factory.Faker('name')
    hashed_password = factory.Faker('password')
    level = factory.Faker('random_int', min=0, max=100)
    is_active = True

class VocabularyFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Vocabulary
        sqlalchemy_session = SessionLocal()

    with open('static/vocabulary.csv', 'r') as f:
        reader = csv.reader(f)
        vocab_list = list(reader)
    random.shuffle(vocab_list)
    for row in vocab_list:
        headword,pos,CEFR,CoreInventory_1,CoreInventory_2,Threshold=row
        word = headword
        word_class = pos
        cefr=lambda CEFR: {'A1':1,'A2':2,'B1':3,'B2':4,'C1':5,'C2':6}[CEFR]
        rank=cefr(CEFR)
        if word_class == 'verb':
            with open('static/verb.csv', 'r') as verb_file:
                reader = csv.reader(verb_file)
                verb_list = list(reader)
            for r in verb_list:
                if r[0] == word:
                    singular = r[1]
                    present_participle = r[2]
                    past_tense = r[3]
                    past_participle = r[4]
        else:
            singular, present_participle, past_tense, past_participle = None, None, None, None
        definition = factory.Faker('sentence')

        Vocabulary(word=word, word_class=word_class, singular=singular, present_participle=present_participle, past_tense=past_tense, past_participle=past_participle, definition=definition, rank=rank)
    
class PersonalDictionaryFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Personal_Dictionary
        sqlalchemy_session = SessionLocal()

    user_id = factory.Faker('random_int', min=1, max=100)
    round_id = factory.Faker('random_int', min=1, max=100)
    vocabulary_id = factory.Faker('random_int', min=1, max=100)
    created_at = factory.Faker('date_time')
    used_times = factory.Faker('random_int', min=0, max=100)
    image_path = factory.Faker('file_path')
    image_height = factory.Faker('random_int', min=0, max=100)
    image_width = factory.Faker('random_int', min=0, max=100)
    image_top = factory.Faker('random_int', min=0, max=100)
    image_left = factory.Faker('random_int', min=0, max=100)
    recent_wrong_spelling = factory.Faker('word')
    note = factory.Faker('sentence')

