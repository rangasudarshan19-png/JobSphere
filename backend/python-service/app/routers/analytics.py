"""
Analytics Router
Endpoints for job application analytics and insights
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List
from datetime import datetime, timedelta, timezone

from app.models.user import User
from app.models.application import Application
from app.utils.database import get_db
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("")
def get_analytics_root(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Shortcut endpoint for analytics summary."""
    return get_analytics_overview(current_user=current_user, db=db)


@router.get("/overview")
def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics overview
    
    Returns:
    - Total applications
    - Status breakdown
    - Success rate
    - Recent activity
    - Top companies
    """
    
    # Get all user applications
    applications = db.query(Application).filter(
        Application.user_id == current_user.id
    ).all()
    
    total_count = len(applications)
    
    if total_count == 0:
        return {
            "total_applications": 0,
            "status_breakdown": {},
            "success_rate": 0,
            "avg_response_time": 0,
            "top_companies": [],
            "recent_activity": []
        }
    
    # Status breakdown
    status_breakdown = {}
    for app in applications:
        status = app.status or "unknown"
        status_breakdown[status] = status_breakdown.get(status, 0) + 1
    
    # Success rate (offers / total)
    offers = status_breakdown.get("offer", 0)
    success_rate = round((offers / total_count) * 100, 2) if total_count > 0 else 0
    
    # Top companies (by application count)
    company_counts = {}
    for app in applications:
        try:
            company_name = app.company.name if (app.company and hasattr(app.company, 'name')) else (app.job_title if app.job_title else "Unknown")
        except:
            company_name = app.job_title if app.job_title else "Unknown"
        company_counts[company_name] = company_counts.get(company_name, 0) + 1
    
    top_companies = [
        {"name": name, "count": count}
        for name, count in sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    # Recent activity (last 7 days)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_apps = []
    for app in applications:
        if app.applied_date and app.applied_date >= seven_days_ago.date():
            try:
                company_name = app.company.name if (app.company and hasattr(app.company, 'name')) else "Unknown"
            except:
                company_name = "Unknown"
            recent_apps.append({
                "id": app.id,
                "job_title": app.job_title,
                "company": company_name,
                "status": app.status,
                "applied_date": app.applied_date.isoformat() if app.applied_date else None
            })
    recent_apps = sorted(recent_apps, key=lambda x: x["applied_date"] or "", reverse=True)
    
    return {
        "total_applications": total_count,
        "status_breakdown": status_breakdown,
        "success_rate": success_rate,
        "top_companies": top_companies,
        "recent_activity": recent_apps[:10]
    }


@router.get("/timeline")
def get_application_timeline(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get application timeline data for the last N days
    
    Returns daily application counts for charts
    """
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get applications in date range
    applications = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.applied_date >= start_date
    ).all()
    
    # Group by date
    date_counts = {}
    for app in applications:
        if app.applied_date:
            date_key = app.applied_date.date().isoformat()
            date_counts[date_key] = date_counts.get(date_key, 0) + 1
    
    # Create timeline with all dates (including zeros)
    timeline = []
    current_date = start_date.date()
    end_date = datetime.now(timezone.utc).date()
    
    while current_date <= end_date:
        date_str = current_date.isoformat()
        timeline.append({
            "date": date_str,
            "count": date_counts.get(date_str, 0)
        })
        current_date += timedelta(days=1)
    
    return {
        "timeline": timeline,
        "total_in_period": sum(date_counts.values()),
        "days": days
    }


@router.get("/status-distribution")
def get_status_distribution(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed status distribution for pie charts
    
    Returns counts and percentages for each status
    """
    
    # Get status counts using SQL grouping
    status_data = db.query(
        Application.status,
        func.count(Application.id).label('count')
    ).filter(
        Application.user_id == current_user.id
    ).group_by(
        Application.status
    ).all()
    
    total = sum(item.count for item in status_data)
    
    if total == 0:
        return {
            "distribution": [],
            "total": 0
        }
    
    distribution = [
        {
            "status": item.status or "unknown",
            "count": item.count,
            "percentage": round((item.count / total) * 100, 2)
        }
        for item in status_data
    ]
    
    # Sort by count descending
    distribution = sorted(distribution, key=lambda x: x["count"], reverse=True)
    
    return {
        "distribution": distribution,
        "total": total
    }


@router.get("/company-insights")
def get_company_insights(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get insights about companies you've applied to
    
    Returns:
    - Company application counts
    - Success rates per company
    - Average response time per company
    """
    
    applications = db.query(Application).filter(
        Application.user_id == current_user.id
    ).all()
    
    if not applications:
        return {
            "companies": [],
            "total_companies": 0
        }
    
    # Group by company
    company_data = {}
    for app in applications:
        try:
            company_name = app.company.name if (app.company and hasattr(app.company, 'name')) else (app.job_title if app.job_title else "Unknown")
        except:
            company_name = app.job_title if app.job_title else "Unknown"
        
        if company_name not in company_data:
            company_data[company_name] = {
                "name": company_name,
                "total_applications": 0,
                "statuses": {},
                "offers": 0
            }
        
        company_data[company_name]["total_applications"] += 1
        
        status = app.status or "unknown"
        company_data[company_name]["statuses"][status] = \
            company_data[company_name]["statuses"].get(status, 0) + 1
        
        if status == "offer":
            company_data[company_name]["offers"] += 1
    
    # Calculate success rates
    companies = []
    for name, data in company_data.items():
        success_rate = round(
            (data["offers"] / data["total_applications"]) * 100, 2
        ) if data["total_applications"] > 0 else 0
        
        companies.append({
            "name": name,
            "applications": data["total_applications"],
            "offers": data["offers"],
            "success_rate": success_rate,
            "statuses": data["statuses"]
        })
    
    # Sort by application count
    companies = sorted(companies, key=lambda x: x["applications"], reverse=True)
    
    return {
        "companies": companies[:limit],
        "total_companies": len(companies)
    }


@router.get("/monthly-stats")
def get_monthly_statistics(
    months: int = 6,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get monthly application statistics for the last N months
    
    Returns aggregated data by month
    """
    
    start_date = datetime.now(timezone.utc) - timedelta(days=months * 30)
    
    applications = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.applied_date >= start_date
    ).all()
    
    # Group by month
    monthly_data = {}
    for app in applications:
        if app.applied_date:
            month_key = app.applied_date.strftime("%Y-%m")
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "month": month_key,
                    "total": 0,
                    "statuses": {}
                }
            
            monthly_data[month_key]["total"] += 1
            status = app.status or "unknown"
            monthly_data[month_key]["statuses"][status] = \
                monthly_data[month_key]["statuses"].get(status, 0) + 1
    
    # Convert to list and sort by month
    monthly_stats = sorted(monthly_data.values(), key=lambda x: x["month"])
    
    return {
        "monthly_stats": monthly_stats,
        "total_months": len(monthly_stats)
    }
