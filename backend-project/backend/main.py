from typing import Union

from fastapi import FastAPI, responses, HTTPException
from sql_app.main import app as subapi

app = FastAPI()

app.mount("/sqlapp", subapi)




