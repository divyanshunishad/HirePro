import requests
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy.orm import Session
from models import RegularJob, FreshersJob, InternshipJob
from config import get_db, logger, engine
from sqlalchemy import inspect
import time
from requests.exceptions import RequestException
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Dict, Any, Type
import backoff
from datetime import datetime

class ScrapingError(Exception):
    """Custom exception for scraping errors"""
    pass

def ensure_tables_exist():
    """Ensure all required tables exist in the database"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    required_tables = ['regular_jobs', 'freshers_jobs', 'internship_jobs']
    
    for table in required_tables:
        if table not in existing_tables:
            logger.info(f"Creating table: {table}")
            if table == 'regular_jobs':
                RegularJob.__table__.create(engine)
            elif table == 'freshers_jobs':
                FreshersJob.__table__.create(engine)
            elif table == 'internship_jobs':
                InternshipJob.__table__.create(engine)

@backoff.on_exception(
    backoff.expo,
    (RequestException, SQLAlchemyError),
    max_tries=3,
    max_time=30
)
def make_request(url: str) -> requests.Response:
    """Make HTTP request with retry logic"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response

def extract_job_details(job_element: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Extract job details from HTML element with error handling"""
    try:
        # Get the job title and company
        title_elem = job_element.find('h2', class_='job-title')
        company_elem = job_element.find('div', class_='company')
        
        # Get location
        location_elem = job_element.find('div', class_='job-location')
        
        # Get salary
        salary_elem = job_element.find('div', class_='job-salary')
        
        # Get job type
        job_type_elem = job_element.find('div', class_='job-category')
        
        # Get posted date
        posted_elem = job_element.find('div', class_='job-posted')
        
        # Get skills
        skills_elem = job_element.find('div', class_='job-skills')
        
        # Get apply URL
        apply_link = job_element.find('a', class_='job-apply')
        
        # Get company logo
        logo_elem = job_element.find('img', class_='company-image')
        
        return {
            'job_title': title_elem.text.strip() if title_elem else 'N/A',
            'company_location': f"{company_elem.text.strip() if company_elem else 'N/A'} - {location_elem.text.strip() if location_elem else 'N/A'}",
            'salary': salary_elem.text.strip() if salary_elem else 'N/A',
            'job_type': job_type_elem.text.strip() if job_type_elem else 'N/A',
            'posted': posted_elem.text.strip() if posted_elem else 'N/A',
            'skills': skills_elem.text.strip() if skills_elem else 'N/A',
            'eligible_years': 'N/A',  # Not available in current structure
            'apply_url': apply_link['href'] if apply_link else 'N/A',
            'company_logo': logo_elem['src'] if logo_elem else None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
    except (AttributeError, KeyError) as e:
        logger.error(f"Error extracting job details: {str(e)}")
        return None

def get_job_model(source_type: str) -> Type:
    """Get the appropriate job model based on source type"""
    model_map = {
        "Regular": RegularJob,
        "Freshers": FreshersJob,
        "Internships": InternshipJob
    }
    return model_map.get(source_type)

def scrape_and_save_jobs(source_type: str) -> None:
    """Scrape and save jobs for a specific source type"""
    db = next(get_db())
    JobModel = get_job_model(source_type)
    
    if not JobModel:
        raise ValueError(f"Invalid source type: {source_type}")
    
    try:
        # Clear existing jobs for this source
        db.query(JobModel).delete()
        db.commit()
        logger.info(f"Cleared existing {source_type} jobs")
        
        # Determine URL based on source type
        url_map = {
            "Regular": "https://www.talentd.in/jobs",
            "Freshers": "https://www.talentd.in/jobs/freshers",
            "Internships": "https://www.talentd.in/jobs/internships"
        }
        
        url = url_map[source_type]
        logger.info(f"Scraping jobs from {url}")
        
        # Make request with retry logic
        response = make_request(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all job listings
        job_listings = soup.find_all('div', class_='job-listing')
        logger.info(f"Found {len(job_listings)} job listings")
        
        successful_jobs = 0
        for job in job_listings:
            try:
                job_details = extract_job_details(job)
                if not job_details:
                    continue
                    
                # Create new job entry
                new_job = JobModel(**job_details)
                db.add(new_job)
                successful_jobs += 1
                
            except Exception as e:
                logger.error(f"Error processing job: {str(e)}")
                continue
        
        db.commit()
        logger.info(f"Successfully saved {successful_jobs} jobs for {source_type}")
                
    except Exception as e:
        logger.error(f"Error scraping {source_type} jobs: {str(e)}")
        db.rollback()
        raise ScrapingError(f"Failed to scrape {source_type} jobs: {str(e)}")
    finally:
        db.close()

def run_all_scrapers() -> None:
    """Run scrapers for all job types"""
    # Ensure all tables exist
    ensure_tables_exist()
    
    sources = ["Regular", "Freshers", "Internships"]
    for source in sources:
        try:
            logger.info(f"Starting scraper for {source} jobs")
            scrape_and_save_jobs(source)
            time.sleep(2)  # Add delay between requests
        except ScrapingError as e:
            logger.error(f"Scraper failed for {source}: {str(e)}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error in {source} scraper: {str(e)}")
            continue

if __name__ == "__main__":
    try:
        run_all_scrapers()
    except Exception as e:
        logger.error(f"Fatal error in scraper: {str(e)}")
        raise 