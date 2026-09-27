"""
server/main.py

FastAPI Production Backend for SmartEval:
- Async Non-blocking Evaluation Workflows
- Multi-tenancy and Exam Management with OCR caching
- Batch Submissions & Real-Time Status Polling
- Class-wide Analytics & Question Difficulty Breakdown
- OpenAPI Documentation available at /docs
"""

import os
import shutil
import hashlib
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from server.database import get_db, init_db
from server.models import User, Exam, Submission, DetailedBreakdown, FeedbackItem, SubmissionStatus
from server.schemas import (
    UserRegister, UserLogin, UserResponse,
    ExamCreate, ExamResponse,
    SubmissionStatusResponse, SubmissionDetailResponse,
    ExamAnalyticsResponse, QuestionPerformance,
    FeedbackCreate, FeedbackResponse
)
from server.evaluation_service import process_submission_task
from src.ocr_extraction import convert_pdf_to_images, extract_text_from_images

# Initialize Database tables
init_db()

app = FastAPI(
    title="SmartEval API",
    description="Scalable, Asynchronous Automated Answer Sheet Evaluation and Analytics Platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for external frontends (e.g. Next.js, React, mobile apps)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

UPLOAD_DIR = os.path.join("data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------------------------------------
# System & Health
# -------------------------------------------------------------
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "SmartEval API",
        "timestamp": datetime.utcnow().isoformat()
    }

# -------------------------------------------------------------
# Authentication Endpoints
# -------------------------------------------------------------
@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Auth"])
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_pw(user_data.password),
        role=user_data.role or "teacher"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/login", tags=["Auth"])
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    ident = login_data.username_or_email.strip().lower()
    user = db.query(User).filter(
        (func.lower(User.username) == ident) | (func.lower(User.email) == ident)
    ).first()
    
    if not user or (user.hashed_password != hash_pw(login_data.password) and user.hashed_password != login_data.password):
        raise HTTPException(status_code=401, detail="Invalid username/email or password")

    return {
        "access_token": f"token_{user.id}_{user.username}",
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }

# -------------------------------------------------------------
# Exam Management with OCR Caching
# -------------------------------------------------------------
@app.post("/api/exams", response_model=ExamResponse, status_code=status.HTTP_201_CREATED, tags=["Exams"])
async def create_exam(
    title: str = Form(...),
    subject_code: str = Form(...),
    rubrics: Optional[str] = Form(None),
    evaluation_mode: str = Form("Reasonable"),
    api_key: str = Form(...),
    question_paper: UploadFile = File(...),
    answer_key: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Creates an Exam record and performs initial OCR extraction on the Question Paper
    and Answer Key ONCE. All future student evaluations reuse this cached text!
    """
    exam_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    exam_dir = os.path.join(UPLOAD_DIR, f"exam_{subject_code}_{exam_timestamp}")
    os.makedirs(exam_dir, exist_ok=True)

    qp_path = os.path.join(exam_dir, "question_paper.pdf")
    ak_path = os.path.join(exam_dir, "answer_key.pdf")

    with open(qp_path, "wb") as f:
        shutil.copyfileobj(question_paper.file, f)
    with open(ak_path, "wb") as f:
        shutil.copyfileobj(answer_key.file, f)

    # Perform OCR once
    qp_images = convert_pdf_to_images(qp_path)
    ak_images = convert_pdf_to_images(ak_path)

    qp_text = extract_text_from_images(qp_images, api_key=api_key)
    ak_text = extract_text_from_images(ak_images, api_key=api_key)

    new_exam = Exam(
        title=title,
        subject_code=subject_code,
        rubrics=rubrics,
        evaluation_mode=evaluation_mode,
        question_paper_text=qp_text,
        answer_key_text=ak_text
    )
    db.add(new_exam)
    db.commit()
    db.refresh(new_exam)

    return ExamResponse(
        id=new_exam.id,
        title=new_exam.title,
        subject_code=new_exam.subject_code,
        rubrics=new_exam.rubrics,
        evaluation_mode=new_exam.evaluation_mode,
        created_at=new_exam.created_at,
        total_submissions=0
    )

@app.get("/api/exams", response_model=List[ExamResponse], tags=["Exams"])
def list_exams(db: Session = Depends(get_db)):
    exams = db.query(Exam).order_by(Exam.created_at.desc()).all()
    results = []
    for exam in exams:
        count = db.query(Submission).filter(Submission.exam_id == exam.id).count()
        results.append(ExamResponse(
            id=exam.id,
            title=exam.title,
            subject_code=exam.subject_code,
            rubrics=exam.rubrics,
            evaluation_mode=exam.evaluation_mode,
            created_at=exam.created_at,
            total_submissions=count
        ))
    return results

@app.get("/api/exams/{exam_id}", response_model=ExamResponse, tags=["Exams"])
def get_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    count = db.query(Submission).filter(Submission.exam_id == exam.id).count()
    return ExamResponse(
        id=exam.id,
        title=exam.title,
        subject_code=exam.subject_code,
        rubrics=exam.rubrics,
        evaluation_mode=exam.evaluation_mode,
        created_at=exam.created_at,
        total_submissions=count
    )

# -------------------------------------------------------------
# Asynchronous Submissions & Evaluation
# -------------------------------------------------------------
@app.post("/api/exams/{exam_id}/evaluate", response_model=SubmissionStatusResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Evaluations"])
async def submit_paper_for_evaluation(
    exam_id: int,
    background_tasks: BackgroundTasks,
    usn: str = Form(...),
    student_name: Optional[str] = Form(None),
    api_key: str = Form(...),
    answer_sheet: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Submits a student's answer sheet for evaluation.
    Immediately returns HTTP 202 Accepted with status 'QUEUED'.
    Evaluation runs in a non-blocking background task.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    usn_clean = usn.strip().upper()
    sub_dir = os.path.join(UPLOAD_DIR, f"exam_{exam_id}", "submissions")
    os.makedirs(sub_dir, exist_ok=True)
    paper_path = os.path.join(sub_dir, f"{usn_clean}_{int(datetime.utcnow().timestamp())}.pdf")

    with open(paper_path, "wb") as f:
        shutil.copyfileobj(answer_sheet.file, f)

    new_submission = Submission(
        exam_id=exam_id,
        usn=usn_clean,
        student_name=student_name,
        student_paper_path=paper_path,
        status=SubmissionStatus.QUEUED,
        progress_stage="Task queued for processing"
    )
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)

    # Launch background task
    background_tasks.add_task(process_submission_task, new_submission.id, api_key)

    return new_submission

@app.post("/api/exams/{exam_id}/evaluate-batch", tags=["Evaluations"])
async def submit_batch_papers(
    exam_id: int,
    background_tasks: BackgroundTasks,
    api_key: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Batch upload multiple student PDF answer sheets at once.
    The filename is automatically parsed as the Student USN (e.g. '2C30309.pdf' -> '2C30309').
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    queued_submissions = []
    sub_dir = os.path.join(UPLOAD_DIR, f"exam_{exam_id}", "submissions")
    os.makedirs(sub_dir, exist_ok=True)

    for upload in files:
        usn = os.path.splitext(upload.filename)[0].upper()
        paper_path = os.path.join(sub_dir, f"{usn}_{int(datetime.utcnow().timestamp())}.pdf")

        with open(paper_path, "wb") as f:
            shutil.copyfileobj(upload.file, f)

        sub = Submission(
            exam_id=exam_id,
            usn=usn,
            student_paper_path=paper_path,
            status=SubmissionStatus.QUEUED,
            progress_stage="Batch queued"
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

        queued_submissions.append({"id": sub.id, "usn": usn, "status": "QUEUED"})
        background_tasks.add_task(process_submission_task, sub.id, api_key)

    return {
        "message": f"Successfully enqueued {len(queued_submissions)} papers for evaluation",
        "submissions": queued_submissions
    }

@app.get("/api/submissions/{submission_id}", response_model=SubmissionDetailResponse, tags=["Evaluations"])
def get_submission_status(submission_id: int, db: Session = Depends(get_db)):
    """Check evaluation status and results for a submission."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub

# -------------------------------------------------------------
# Analytics & Student Portals
# -------------------------------------------------------------
@app.get("/api/exams/{exam_id}/analytics", response_model=ExamAnalyticsResponse, tags=["Analytics"])
def get_exam_analytics(exam_id: int, db: Session = Depends(get_db)):
    """Calculates class-level performance, pass/fail metrics, and question difficulty."""
    subs = db.query(Submission).filter(
        Submission.exam_id == exam_id,
        Submission.status == SubmissionStatus.COMPLETED
    ).all()

    total_count = db.query(Submission).filter(Submission.exam_id == exam_id).count()
    completed_count = len(subs)
    pending_count = total_count - completed_count

    if not subs:
        return ExamAnalyticsResponse(
            exam_id=exam_id,
            total_papers=total_count,
            evaluated=0,
            pending=pending_count,
            completion_rate=0.0,
            class_average=0.0,
            pass_count=0,
            fail_count=0,
            pass_rate=0.0,
            question_difficulty=[]
        )

    scores = [s.percentage for s in subs if s.percentage is not None]
    class_avg = sum(scores) / len(scores) if scores else 0.0
    pass_count = sum(1 for s in scores if s >= 40.0)
    fail_count = len(scores) - pass_count
    pass_rate = round((pass_count / len(scores)) * 100, 2) if scores else 0.0

    # Question difficulty breakdown
    breakdowns = db.query(
        DetailedBreakdown.question,
        func.avg(DetailedBreakdown.marks_awarded / func.nullif(DetailedBreakdown.max_marks, 0) * 100).label("avg_score")
    ).join(Submission).filter(
        Submission.exam_id == exam_id,
        Submission.status == SubmissionStatus.COMPLETED
    ).group_by(DetailedBreakdown.question).order_by("avg_score").all()

    difficulty_list = [
        QuestionPerformance(question=q, average_score=round(float(score or 0), 2))
        for q, score in breakdowns
    ]

    return ExamAnalyticsResponse(
        exam_id=exam_id,
        total_papers=total_count,
        evaluated=completed_count,
        pending=pending_count,
        completion_rate=round((completed_count / total_count * 100), 2) if total_count > 0 else 0.0,
        class_average=round(class_avg, 2),
        pass_count=pass_count,
        fail_count=fail_count,
        pass_rate=pass_rate,
        question_difficulty=difficulty_list
    )

@app.get("/api/students/{usn}/results", response_model=List[SubmissionDetailResponse], tags=["Students"])
def get_student_results(usn: str, db: Session = Depends(get_db)):
    """Student portal endpoint to retrieve all evaluated papers for a USN."""
    results = db.query(Submission).filter(
        func.upper(Submission.usn) == usn.strip().upper(),
        Submission.status == SubmissionStatus.COMPLETED
    ).order_by(Submission.completed_at.desc()).all()
    return results

# -------------------------------------------------------------
# Feedback Hub
# -------------------------------------------------------------
@app.post("/api/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED, tags=["Feedback"])
def submit_feedback(fb: FeedbackCreate, db: Session = Depends(get_db)):
    new_fb = FeedbackItem(
        usn=fb.usn,
        role=fb.role or "student",
        rating=fb.rating,
        comment=fb.comment,
        subject=fb.subject or "General"
    )
    db.add(new_fb)
    db.commit()
    db.refresh(new_fb)
    return new_fb

@app.get("/api/feedback", response_model=List[FeedbackResponse], tags=["Feedback"])
def get_feedbacks(db: Session = Depends(get_db)):
    return db.query(FeedbackItem).order_by(FeedbackItem.created_at.desc()).all()
