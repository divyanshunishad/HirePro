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
from urllib.parse import urljoin
import html

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

def clean_salary(salary: str) -> str:
    """Clean salary string"""
    if not salary:
        return ""
    return salary.replace("\u20b9", "INR").replace("₹", "INR").replace("?", "INR").strip()

def clean_text(text: str) -> str:
    """Clean text string"""
    return html.unescape(text.strip()) if text else ""

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

def extract_job_details(job_element: BeautifulSoup, base_url: str) -> Optional[Dict[str, Any]]:
    """Extract job details from HTML element with error handling"""
    try:
        # Get the job title
        title = clean_text(job_element.select_one("h2.text-lg").text) if job_element.select_one("h2.text-lg") else ""
        
        # Get company and location
        company_location = clean_text(job_element.select_one("p.text-gray-600").text) if job_element.select_one("p.text-gray-600") else ""
        
        # Get salary
        salary_raw = clean_text(job_element.select_one("p.text-green-600").text) if job_element.select_one("p.text-green-600") else ""
        salary = clean_salary(salary_raw)
        
        # Get posted date
        posted_date = clean_text(job_element.select_one("p.text-gray-500").text) if job_element.select_one("p.text-gray-500") else ""
        
        # Get tags (years and job type)
        tags = job_element.select("div.mt-2 span.text-sm")
        years = clean_text(tags[0].text) if len(tags) > 0 else ""
        job_type = clean_text(tags[1].text) if len(tags) > 1 else ""
        
        # Get skills
        skills_list = [clean_text(s.text) for s in job_element.select("div.flex-wrap.gap-2.mt-3 span")]
        skills = ", ".join(skills_list)
        
        # Get apply URL
        apply_button = job_element.select_one("a.bg-blue-600")
        apply_url = urljoin(base_url, apply_button["href"]) if apply_button and "href" in apply_button.attrs else ""
        
        # Get company logo
        img_tag = job_element.select_one("img.rounded-lg")
        logo_url = urljoin(base_url, img_tag["src"]) if img_tag and "src" in img_tag.attrs else ""
        
        return {
            'job_title': title,
            'company_location': company_location,
            'salary': salary,
            'job_type': job_type,
            'posted': posted_date,
            'skills': skills,
            'eligible_years': years,
            'apply_url': apply_url,
            'company_logo': logo_url,
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
            "Regular": "https://www.talentd.in/jobs?page=",
            "Freshers": "https://www.talentd.in/jobs/freshers?page=",
            "Internships": "https://www.talentd.in/jobs/internships?page="
        }
        
        base_url = url_map[source_type]
        
        # Get first page to detect total pages
        first_page = make_request(base_url + "1")
        soup = BeautifulSoup(first_page.text, "html.parser")
        pagination = soup.select("div.hidden.sm\\:flex a[href*='page=']")
        last_page = max([int(a.text.strip()) for a in pagination if a.text.strip().isdigit()] or [1])
        logger.info(f"Total pages detected for {source_type}: {last_page}")
        
        successful_jobs = 0
        for page in range(1, last_page + 1):
            logger.info(f"Scraping page {page} of {last_page} for {source_type}...")
            response = make_request(base_url + str(page))
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find all job listings
            job_cards = soup.find_all("div", class_="!bg-white/80 backdrop-blur-sm rounded-xl border border-gray-200/50 p-4 hover:shadow-lg transition-all hover:border-blue-200/50")
            logger.info(f"Found {len(job_cards)} jobs on page {page}")
            
            for job in job_cards:
                try:
                    job_details = extract_job_details(job, base_url)
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
            time.sleep(2)  # Add delay between pages
        
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
            time.sleep(2)  # Add delay between sources
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