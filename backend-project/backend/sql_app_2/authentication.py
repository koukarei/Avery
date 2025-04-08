from datetime import datetime, timedelta, timezone,date
from typing import Annotated, Union,Literal, Optional

from fastapi import Depends,HTTPException, status, Header,Cookie
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from .schemas import TokenData
from . import crud

# to get a string like this run:
# openssl rand -hex 32
import os
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/sqlapp2/token",auto_error=False,)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(
        db, 
        username: str, 
        password: str
):
    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=400, detail="The user does not exist.")
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    return user

def authenticate_user_2(
        db,
        lti_user_id: int,
        school: str
):
    user = crud.get_user_by_lti(db, lti_user_id, school)
    if not user:
        raise HTTPException(status_code=400, detail="The user does not exist.")
    return user

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt

def create_refresh_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": username, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt