from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    CompanyCreate,
    CompanyResponse
)
from app.models.application import Application, Company
from app.models.user import User
from app.utils.database import get_db
from app.routers.auth import get_current_user
from app.services.email_service import email_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/applications", tags=["Applications"])


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    application: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new job application"""
    logger.info(f"Creating application for user: {current_user.email}")
    logger.info(f"Application data received:")
    logger.info(f"   - Job: {application.job_title}")
    logger.info(f"   - Company: {application.company_name}")
    logger.info(f"   - Next Phase Date: {application.next_phase_date}")
    logger.info(f"   - Next Phase Type: {application.next_phase_type}")
    logger.info(f"   - Applied Date: {application.applied_date}")
    logger.info(f"   - Notes: {application.notes[:50] if application.notes else 'None'}...")
    
    # Handle company
    company_id = application.company_id
    if not company_id and application.company_name:
        # Check if company exists
        company = db.query(Company).filter(Company.name == application.company_name).first()
        if not company:
            # Create new company
            company = Company(name=application.company_name)
            db.add(company)
            db.commit()
            db.refresh(company)
        company_id = company.id
    
    # Create application
    db_application = Application(
        user_id=current_user.id,
        company_id=company_id,
        job_title=application.job_title,
        job_description=application.job_description,
        job_url=application.job_url,
        status=application.status,
        salary_range=application.salary_range,
        location=application.location,
        job_type=application.job_type,
        applied_date=application.applied_date,
        deadline=application.deadline,
        notes=application.notes,
        next_phase_date=application.next_phase_date if hasattr(application, 'next_phase_date') else None,
        next_phase_type=application.next_phase_type if hasattr(application, 'next_phase_type') else None,
        interview_date=application.interview_date if hasattr(application, 'interview_date') else None,
        interview_time=application.interview_time if hasattr(application, 'interview_time') else None,
        interview_details=application.interview_details if hasattr(application, 'interview_details') else None,
        send_notifications=application.send_notifications if hasattr(application, 'send_notifications') else True
    )
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    
    # Send application created email (non-blocking) if notifications enabled
    try:
        if db_application.send_notifications:
            logger.info(f"Sending application created email to {current_user.email}")
            
            # Get company name
            company_name = "Unknown Company"
            if db_application.company:
                company_name = db_application.company.name
            elif application.company_name:
                company_name = application.company_name
            
            # Format next phase date if present
            next_phase_date_str = None
            if db_application.next_phase_date:
                next_phase_date_str = db_application.next_phase_date.strftime("%B %d, %Y")
            
            # Format interview date and time if present
            interview_date_str = None
            interview_time_str = None
            if db_application.interview_date:
                interview_date_str = db_application.interview_date.strftime("%B %d, %Y")
            if db_application.interview_time:
                interview_time_str = db_application.interview_time.strftime("%I:%M %p")
            
            # Send standard application created email with notes
            email_service.send_application_created_email(
                to_email=current_user.email,
                user_name=current_user.full_name or "User",
                company=company_name,
                position=db_application.job_title or "Position",
                location=db_application.location or "Not specified",
                status=db_application.status or "Applied",
                user_notes=db_application.notes or "",
                next_phase_date=next_phase_date_str,
                next_phase_type=db_application.next_phase_type,
                interview_date=interview_date_str,
                interview_time=interview_time_str,
                interview_details=db_application.interview_details or "",
                application_id=db_application.id
            )
            
            # If next phase is today, send special "Good Luck Today" email with AI tips
            if db_application.next_phase_date:
                from datetime import date
                # next_phase_date is already a date object, not datetime
                today = date.today()
                logger.info(f"Checking next phase date: {db_application.next_phase_date} vs today: {today}")
                if db_application.next_phase_date == today:
                    logger.info(f"Next phase is TODAY! Sending special AI-powered good luck email")
                    email_service.send_next_phase_today_email(
                        to_email=current_user.email,
                        user_name=current_user.full_name or "User",
                        company=company_name,
                        position=db_application.job_title or "Position",
                        phase_type=db_application.next_phase_type or "Interview",
                        phase_time=interview_time_str or "as scheduled",
                        location=db_application.location or "TBD",
                        job_description=db_application.job_description or "",
                        user_notes=db_application.notes or "",
                        application_id=db_application.id
                    )
                else:
                    logger.info(f"Next phase is NOT today ({db_application.next_phase_date} != {today})")
        else:
            logger.info(f"Notifications disabled for this application - skipping email")
    except Exception as e:
        # Don't fail application creation if email fails
        logger.error(f"Failed to send application created email: {str(e)}")
    
    return db_application


@router.get("", response_model=List[ApplicationResponse])
def list_applications(
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all applications for the current user"""
    query = db.query(Application).filter(Application.user_id == current_user.id)
    
    if status:
        query = query.filter(Application.status == status)
    
    applications = query.offset(skip).limit(limit).all()
    return applications


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific application"""
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    return application


@router.put("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: int,
    application_update: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an application"""
    db_application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    
    if not db_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Store old status for notification
    old_status = db_application.status
    
    # Update fields
    update_data = application_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_application, field, value)
    
    db.commit()
    db.refresh(db_application)
    
    # Send notification if status changed and notifications enabled
    if 'status' in update_data and old_status != db_application.status and db_application.send_notifications:
        try:
            logger.info(f"Sending status change email: {old_status} -> {db_application.status}")
            
            # Get company name
            company_name = "Unknown Company"
            if db_application.company:
                company_name = db_application.company.name
            
            # Format interview date and time if present
            interview_date_str = None
            interview_time_str = None
            if db_application.interview_date:
                interview_date_str = db_application.interview_date.strftime("%B %d, %Y")
            if db_application.interview_time:
                interview_time_str = db_application.interview_time.strftime("%I:%M %p")
            
            email_service.send_application_status_changed_email(
                to_email=current_user.email,
                user_name=current_user.full_name or "User",
                company=company_name,
                position=db_application.job_title or "Position",
                old_status=old_status,
                new_status=db_application.status,
                location=db_application.location or "Not specified",
                interview_date=interview_date_str,
                interview_time=interview_time_str,
                interview_details=db_application.interview_details or "",
                user_notes=db_application.notes or "",
                application_id=db_application.id
            )
        except Exception as e:
            logger.error(f"Failed to send status change email: {str(e)}")
    
    return db_application


@router.patch("/{application_id}", response_model=ApplicationResponse)
def partial_update_application(
    application_id: int,
    application_update: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Partially update an application (e.g., just status for drag & drop)"""
    db_application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    
    if not db_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Store old status for notification
    old_status = db_application.status
    
    # Update only provided fields
    update_data = application_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_application, field, value)
    
    db.commit()
    db.refresh(db_application)
    
    # Send notification if status changed and notifications enabled
    if 'status' in update_data and old_status != db_application.status and db_application.send_notifications:
        try:
            logger.info(f"Sending status change email: {old_status} -> {db_application.status}")
            
            # Get company name
            company_name = "Unknown Company"
            if db_application.company:
                company_name = db_application.company.name
            
            # Format interview date and time if present
            interview_date_str = None
            interview_time_str = None
            if db_application.interview_date:
                interview_date_str = db_application.interview_date.strftime("%B %d, %Y")
            if db_application.interview_time:
                interview_time_str = db_application.interview_time.strftime("%I:%M %p")
            
            email_service.send_application_status_changed_email(
                to_email=current_user.email,
                user_name=current_user.full_name or "User",
                company=company_name,
                position=db_application.job_title or "Position",
                old_status=old_status,
                new_status=db_application.status,
                location=db_application.location or "Not specified",
                interview_date=interview_date_str,
                interview_time=interview_time_str,
                interview_details=db_application.interview_details or "",
                user_notes=db_application.notes or "",
                application_id=db_application.id
            )
        except Exception as e:
            logger.error(f"Failed to send status change email: {str(e)}")
    
    return db_application


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an application"""
    db_application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    
    if not db_application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    db.delete(db_application)
    db.commit()
    
    return None


@router.get("/stats/summary")
def get_application_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get application statistics"""
    total = db.query(Application).filter(Application.user_id == current_user.id).count()
    
    status_counts = {}
    statuses = ["applied", "screening", "interview_scheduled", "interviewed", "offer", "rejected"]
    for status_name in statuses:
        count = db.query(Application).filter(
            Application.user_id == current_user.id,
            Application.status == status_name
        ).count()
        status_counts[status_name] = count
    
    return {
        "total_applications": total,
        "by_status": status_counts
    }
