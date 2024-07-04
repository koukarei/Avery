from typing import Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
from datetime import date

class UserIn(BaseModel):
    id: Optional[str] = Field(None, title="User ID")
    username: str = Field(...,min_length=6,max_length=20, title="User Name")
    email: str = Field(..., title="User Email")
    password: str = Field(...,min_length=8,max_length=20, title="User Password")
    date_joined: Optional[date] = Field(None, title="User Date Joined")
    is_active: Optional[bool] = Field(None, title="User Active Status")
    is_admin: Optional[bool] = Field(None, title="User Admin Status")

class UserOut(BaseModel):
    id: Optional[str] = Field(None, title="User ID")
    username: str = Field(..., title="User Name")
    email: str = Field(..., title="User Email")
    date_joined: Optional[date] = Field(None, title="User Date Joined")
    is_active: Optional[bool] = Field(None, title="User Active Status")
    is_admin: Optional[bool] = Field(None, title="User Admin Status")