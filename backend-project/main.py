from typing import Union

from fastapi import FastAPI
from sql_app.main import app as subapi

app = FastAPI()

app.mount("/subapi", subapi)

@app.get("/")
def read_root():
    return {"Hello": "World"}
