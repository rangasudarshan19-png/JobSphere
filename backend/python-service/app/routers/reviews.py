from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

from app.models.review import Review
from app.models.user import User
from app.utils.database import get_db
from app.routers.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])


# ── Schemas ──────────────────────────────────────────────

class ReviewCreate(BaseModel):
    rating: int
    title: str
    content: str
    reviewer_name: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        v = v.strip()
        if len(v) < 3 or len(v) > 200:
            raise ValueError("Title must be 3-200 characters")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        v = v.strip()
        if len(v) < 10 or len(v) > 2000:
            raise ValueError("Review must be 10-2000 characters")
        return v


class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError("Rating must be between 1 and 5")
        return v


class ReviewResponse(BaseModel):
    id: int
    rating: int
    title: str
    content: str
    reviewer_name: str
    created_at: datetime
    is_own: bool = False

    model_config = {"from_attributes": True}


# ── Public endpoints (no auth) ───────────────────────────

@router.get("")
def get_reviews(db: Session = Depends(get_db)):
    """Get all approved reviews (public - no auth required)"""
    reviews = (
        db.query(Review)
        .filter(Review.is_approved == 1)
        .order_by(Review.created_at.desc())
        .limit(50)
        .all()
    )

    # Compute average rating
    avg_result = (
        db.query(func.avg(Review.rating))
        .filter(Review.is_approved == 1)
        .scalar()
    )
    avg_rating = round(float(avg_result), 1) if avg_result else 0

    total = (
        db.query(func.count(Review.id))
        .filter(Review.is_approved == 1)
        .scalar()
    )

    return {
        "reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "title": r.title,
                "content": r.content,
                "reviewer_name": r.reviewer_name,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reviews
        ],
        "average_rating": avg_rating,
        "total_reviews": total,
    }


# ── Authenticated endpoints ──────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
def create_review(
    review: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a new review (one per user)"""
    # Check if user already reviewed
    existing = db.query(Review).filter(Review.user_id == current_user.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a review. You can edit or delete your existing review.",
        )

    display_name = (review.reviewer_name or "").strip() or current_user.full_name

    new_review = Review(
        user_id=current_user.id,
        rating=review.rating,
        title=review.title,
        content=review.content,
        reviewer_name=display_name,
        is_approved=1,
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    logger.info(f"New review by {current_user.email}: {review.rating} stars")

    return {
        "message": "Review submitted successfully!",
        "review": {
            "id": new_review.id,
            "rating": new_review.rating,
            "title": new_review.title,
            "content": new_review.content,
            "reviewer_name": new_review.reviewer_name,
            "created_at": new_review.created_at.isoformat() if new_review.created_at else None,
        },
    }


@router.get("/mine")
def get_my_review(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current user's review (if any)"""
    review = db.query(Review).filter(Review.user_id == current_user.id).first()
    if not review:
        return {"review": None}

    return {
        "review": {
            "id": review.id,
            "rating": review.rating,
            "title": review.title,
            "content": review.content,
            "reviewer_name": review.reviewer_name,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        }
    }


@router.put("/{review_id}")
def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update own review"""
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.user_id == current_user.id,
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found or not yours")

    if review_data.rating is not None:
        review.rating = review_data.rating
    if review_data.title is not None:
        review.title = review_data.title.strip()
    if review_data.content is not None:
        review.content = review_data.content.strip()

    review.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(review)

    logger.info(f"Review {review_id} updated by {current_user.email}")

    return {
        "message": "Review updated successfully!",
        "review": {
            "id": review.id,
            "rating": review.rating,
            "title": review.title,
            "content": review.content,
            "reviewer_name": review.reviewer_name,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        },
    }


@router.delete("/{review_id}")
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete own review"""
    review = db.query(Review).filter(
        Review.id == review_id,
        Review.user_id == current_user.id,
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found or not yours")

    db.delete(review)
    db.commit()

    logger.info(f"Review {review_id} deleted by {current_user.email}")
    return {"message": "Review deleted successfully"}
