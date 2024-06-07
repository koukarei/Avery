import time
import uuid
from typing import List
class Round():

    def __init__(self):
        timestamp = str(int(time.time()))
        unique_id = uuid.uuid4().hex
        self.id=f"ID-{timestamp}-{unique_id}"
        self.original_picture=None
        self.keyword=[]
        self.sentence=None

    def set_original_picture(self,img):
        self.original_picture = img
        #with open(picture_path,'rb') as image_file:
        #    self.original_picture = image_file.read()
        return "Original picture set"

    def set_keyword(self,keyword: List[str]):
        self.keyword=keyword

    def set_sentence(self,sentence):
        self.sentence=sentence

