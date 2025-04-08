from typing import Union

from fastapi import FastAPI, responses, HTTPException
from sql_app.main import app as subapi
from sql_app_2.main import app as subapi_2

app = FastAPI()

app.mount("/sqlapp", subapi)

app.mount("/sqlapp2", subapi_2)




