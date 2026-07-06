# -*- coding: utf-8 -*-
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

# --- User Schema ---
class UserCreate(BaseModel):
    name: str = Field(..., max_length=50)
    phone: str = Field(..., max_length=20)
    disability_severity: str = Field(..., max_length=50)

class UserResponse(BaseModel):
    user_id: int
    name: str
    phone: str
    disability_severity: str
    status: str
    model_config = ConfigDict(from_attributes=True)

# --- Device Schema ---
class DeviceCreate(BaseModel):
    device_uuid: str = Field(..., max_length=100)
    platform: str = Field("unknown", max_length=20)

class DeviceResponse(BaseModel):
    device_id: int
    user_id: int
    device_uuid: str
    platform: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

# --- Admin Schema ---
class AdminCreate(BaseModel):
    employee_no: str = Field(..., max_length=50)
    name: str = Field(..., max_length=50)
    password: str = Field(..., min_length=4, max_length=100)
    role: str = Field("operator", max_length=20)

class AdminResponse(BaseModel):
    admin_id: int
    employee_no: str
    name: str
    role: str
    status: str
    model_config = ConfigDict(from_attributes=True)

# --- Auth Schema ---
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
