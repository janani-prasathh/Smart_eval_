"""
server/schemas.py

Pydantic schemas for data validation and OpenAPI serialization.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from server.models import SubmissionStatus

# --- User Schemas ---
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[str] = "teacher"

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Exam Schemas ---
class ExamCreate(BaseModel):
    title: str
    subject_code: str
    rubrics: Optional[str] = None
    evaluation_mode: Optional[str] = "Reasonable"

class ExamResponse(BaseModel):
    id: int
    title: str
    subject_code: str
    rubrics: Optional[str]
    evaluation_mode: str
    created_at: datetime
    total_submissions: Optional[int] = 0

    class Config:
        from_attributes = True

# --- Breakdown & Submission Schemas ---
class BreakdownItem(BaseModel):
    question: str
    part: Optional[str] = ""
    description: Optional[str] = None
    feedback: Optional[str] = None
    marks_awarded: float
    max_marks: float

    class Config:
        from_attributes = True

class SubmissionStatusResponse(BaseModel):
    id: int
    exam_id: int
    usn: str
    status: SubmissionStatus
    progress_stage: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SubmissionDetailResponse(BaseModel):
    id: int
    exam_id: int
    usn: str
    status: SubmissionStatus
    diagram_count: int
    score_awarded: Optional[float] = None
    max_score: Optional[float] = None
    percentage: Optional[float] = None
    evaluation_report: Optional[str] = None
    breakdowns: List[BreakdownItem] = []
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Analytics Schemas ---
class QuestionPerformance(BaseModel):
    question: str
    average_score: float

class ExamAnalyticsResponse(BaseModel):
    exam_id: int
    total_papers: int
    evaluated: int
    pending: int
    completion_rate: float
    class_average: float
    pass_count: int
    fail_count: int
    pass_rate: float
    question_difficulty: List[QuestionPerformance] = []

# --- Feedback Schemas ---
class FeedbackCreate(BaseModel):
    usn: str
    role: Optional[str] = "student"
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    subject: Optional[str] = "General"

class FeedbackResponse(BaseModel):
    id: int
    usn: str
    role: str
    rating: int
    comment: Optional[str]
    subject: str
    created_at: datetime

    class Config:
        from_attributes = True
