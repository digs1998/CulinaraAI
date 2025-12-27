"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel, EmailStr, Field
from typing import List
from enum import Enum

class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class CookingTime(str, Enum):
    QUICK = "quick"
    MEDIUM = "medium"
    LONG = "long"

class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    dietary_restrictions: List[str] = Field(default=[])
    cuisine_preferences: List[str] = Field(default=[])
    skill_level: str = Field(default="beginner")
    cooking_time: str = Field(default="medium")
    allergies: List[str] = Field(default=[])
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "dietary_restrictions": ["vegetarian"],
                "cuisine_preferences": ["italian", "mediterranean"],
                "skill_level": "beginner",
                "cooking_time": "medium",
                "allergies": ["nuts"]
            }
        }

class SignupResponse(BaseModel):
    user_id: int
    message: str

class ChatRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    message: str = Field(..., min_length=1, max_length=1000)

class ChatResponse(BaseModel):
    response: str

class FactResponse(BaseModel):
    fact: str

class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"

class ErrorResponse(BaseModel):
    detail: str