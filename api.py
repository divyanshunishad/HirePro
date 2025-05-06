from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from models import RegularJob, FreshersJob, InternshipJob, Base
from config import get_db, engine, logger
from pydantic import BaseModel, HttpUrl, validator
from datetime import datetime
import time
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from scraper import run_all_scrapers
import logging

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="HirePro Jobs API",
    description="API for accessing job listings from talentd.in",
    version="1.0.0"
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables with error handling
try:
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error creating database tables: {str(e)}")
    raise

class JobResponse(BaseModel):
    id: int
    job_title: str
    company_location: str
    salary: str
    job_type: str
    posted: str
    skills: str
    eligible_years: str
    apply_url: HttpUrl
    company_logo: Optional[HttpUrl]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Helper function for job queries
def get_filtered_jobs(db: Session, model_class, search: Optional[str] = None, location: Optional[str] = None):
    query = db.query(model_class)
    
    if search:
        search_terms = search.lower().split()
        for term in search_terms:
            query = query.filter(
                (model_class.job_title.ilike(f"%{term}%")) |
                (model_class.company_location.ilike(f"%{term}%")) |
                (model_class.skills.ilike(f"%{term}%"))
            )
    
    if location:
        query = query.filter(model_class.company_location.ilike(f"%{location}%"))
    
    return query.all()

@app.get("/api/regular-jobs", response_model=List[JobResponse])
@limiter.limit("60/minute")
async def get_regular_jobs(
    request: Request,
    search: Optional[str] = Query(None, description="Search term for job title, company, or skills"),
    location: Optional[str] = Query(None, description="Filter by location"),
    db: Session = Depends(get_db)
):
    """
    Get regular jobs with optional search and location filters.
    Rate limited to 60 requests per minute.
    """
    try:
        jobs = get_filtered_jobs(db, RegularJob, search, location)
        logger.info(f"Retrieved {len(jobs)} regular jobs")
        return jobs
    except Exception as e:
        logger.error(f"Error retrieving regular jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/freshers-jobs", response_model=List[JobResponse])
@limiter.limit("60/minute")
async def get_freshers_jobs(
    request: Request,
    search: Optional[str] = Query(None, description="Search term for job title, company, or skills"),
    location: Optional[str] = Query(None, description="Filter by location"),
    db: Session = Depends(get_db)
):
    """
    Get freshers jobs with optional search and location filters.
    Rate limited to 60 requests per minute.
    """
    try:
        jobs = get_filtered_jobs(db, FreshersJob, search, location)
        logger.info(f"Retrieved {len(jobs)} freshers jobs")
        return jobs
    except Exception as e:
        logger.error(f"Error retrieving freshers jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/internships", response_model=List[JobResponse])
@limiter.limit("60/minute")
async def get_internships(
    request: Request,
    search: Optional[str] = Query(None, description="Search term for job title, company, or skills"),
    location: Optional[str] = Query(None, description="Filter by location"),
    db: Session = Depends(get_db)
):
    """
    Get internship jobs with optional search and location filters.
    Rate limited to 60 requests per minute.
    """
    try:
        jobs = get_filtered_jobs(db, InternshipJob, search, location)
        logger.info(f"Retrieved {len(jobs)} internship jobs")
        return jobs
    except Exception as e:
        logger.error(f"Error retrieving internship jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/jobs/{job_id}", response_model=JobResponse)
@limiter.limit("60/minute")
async def get_job(
    request: Request,
    job_id: int,
    job_type: str = Query(..., description="Type of job (regular/freshers/internships)"),
    db: Session = Depends(get_db)
):
    """
    Get a specific job by ID and type.
    Rate limited to 60 requests per minute.
    """
    try:
        model_map = {
            "regular": RegularJob,
            "freshers": FreshersJob,
            "internships": InternshipJob
        }
        
        if job_type.lower() not in model_map:
            raise HTTPException(status_code=400, detail="Invalid job type")
            
        job = db.query(model_map[job_type.lower()]).filter(model_map[job_type.lower()].id == job_id).first()
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db = next(get_db())
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }

@app.get("/api/scrape")
async def trigger_scrape(db: Session = Depends(get_db)):
    """
    Trigger job scraping and update the database.
    This endpoint is called by the cron job service.
    """
    try:
        # Clear existing jobs from all tables
        db.query(RegularJob).delete()
        db.query(FreshersJob).delete()
        db.query(InternshipJob).delete()
        
        # Scrape new jobs
        run_all_scrapers()
        
        return {"message": "Job scraping completed successfully"}
    except Exception as e:
        logger.error(f"Error during job scraping: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to scrape jobs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 