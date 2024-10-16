from typing import Union

from fastapi import FastAPI, responses, staticfiles
from sql_app.main import app as subapi
from sql_app.main import crud

app = FastAPI()

app.mount("/sqlapp", subapi)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get('/files/{filename}')
async def get_files(filename: str):
    return responses.FileResponse(filename)

app.mount('/', staticfiles.StaticFiles(directory='/static/',html=True))
