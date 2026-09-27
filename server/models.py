"""
server/models.py

SQLAlchemy ORM models representing the core entities of SmartEval:
- User (Teachers & Admins)
- Exam (Question Paper, Answer Key, Rubrics, cached OCR text)
- Submission (Student answer sheet submissions and evaluation status)
- DetailedBreakdown (Itemized per-question feedback & marks)
- FeedbackItem (Student & Faculty reviews)
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from server.database import Base

class SubmissionStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="teacher", nullable=False)  # "teacher" or "admin"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    exams = relationship("Exam", back_populates="creator")

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    subject_code = Column(String(100), index=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Cached OCR text so 100 students sharing the same exam only OCR once!
    question_paper_text = Column(Text, nullable=True)
    answer_key_text = Column(Text, nullable=True)
    rubrics = Column(Text, nullable=True)
    evaluation_mode = Column(String(50), default="Reasonable", nullable=False)

    # Document content hashes for cache invalidation
    question_paper_hash = Column(String(64), nullable=True)
    answer_key_hash = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    creator = relationship("User", back_populates="exams")
    submissions = relationship("Submission", back_populates="exam", cascade="all, delete-orphan")

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False, index=True)
    usn = Column(String(50), index=True, nullable=False)
    student_name = Column(String(150), nullable=True)
    student_paper_path = Column(String(500), nullable=True)
    
    # Asynchronous task state
    status = Column(SQLEnum(SubmissionStatus), default=SubmissionStatus.QUEUED, index=True)
    progress_stage = Column(String(100), default="Queued")
    error_message = Column(Text, nullable=True)

    # Results
    diagram_count = Column(Integer, default=0)
    score_awarded = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)
    evaluation_report = Column(Text, nullable=True)
    analytics_json = Column(Text, nullable=True)  # Raw JSON storage for complex structures

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    exam = relationship("Exam", back_populates="submissions")
    breakdowns = relationship("DetailedBreakdown", back_populates="submission", cascade="all, delete-orphan")

class DetailedBreakdown(Base):
    __tablename__ = "detailed_breakdowns"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    question = Column(String(50), nullable=False)
    part = Column(String(50), default="")
    description = Column(String(255), nullable=True)
    feedback = Column(Text, nullable=True)
    marks_awarded = Column(Float, default=0.0)
    max_marks = Column(Float, default=0.0)

    submission = relationship("Submission", back_populates="breakdowns")

class FeedbackItem(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    usn = Column(String(50), index=True, nullable=False)
    role = Column(String(50), default="student", nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    subject = Column(String(150), default="General", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
