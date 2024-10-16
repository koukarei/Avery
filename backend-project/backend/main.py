from typing import Union

from fastapi import FastAPI, responses, staticfiles
from sql_app.main import app as subapi
from sql_app.main import crud

app = FastAPI()

app.mount("/sqlapp", subapi)

@app.get("/")
def read_root():
    return {"Hello": "World"}
