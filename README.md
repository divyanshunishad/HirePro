# HirePro Jobs API

A FastAPI-based REST API for accessing job listings from talentd.in. The API provides endpoints for regular jobs, freshers jobs, and internships.

## API Endpoints

### Health Check
```
GET https://hirepro-x72c.onrender.com/health
```
Checks the health status of the API and database connection.

### Regular Jobs
```
# Get all regular jobs
GET https://hirepro-x72c.onrender.com/api/regular-jobs

# Search regular jobs
GET https://hirepro-x72c.onrender.com/api/regular-jobs?search=python

# Filter by location
GET https://hirepro-x72c.onrender.com/api/regular-jobs?location=bangalore

# Search and filter combined
GET https://hirepro-x72c.onrender.com/api/regular-jobs?search=python&location=bangalore
```

### Freshers Jobs
```
# Get all freshers jobs
GET https://hirepro-x72c.onrender.com/api/freshers-jobs

# Search freshers jobs
GET https://hirepro-x72c.onrender.com/api/freshers-jobs?search=python

# Filter by location
GET https://hirepro-x72c.onrender.com/api/freshers-jobs?location=bangalore

# Search and filter combined
GET https://hirepro-x72c.onrender.com/api/freshers-jobs?search=python&location=bangalore
```

### Internships
```
# Get all internships
GET https://hirepro-x72c.onrender.com/api/internships

# Search internships
GET https://hirepro-x72c.onrender.com/api/internships?search=python

# Filter by location
GET https://hirepro-x72c.onrender.com/api/internships?location=bangalore

# Search and filter combined
GET https://hirepro-x72c.onrender.com/api/internships?search=python&location=bangalore
```

### Specific Job Details
```
# Get specific job by ID and type
GET https://hirepro-x72c.onrender.com/api/jobs/{job_id}?job_type=regular
GET https://hirepro-x72c.onrender.com/api/jobs/{job_id}?job_type=freshers
GET https://hirepro-x72c.onrender.com/api/jobs/{job_id}?job_type=internships
```

### Scrape Jobs (Admin/Update)
```
GET https://hirepro-x72c.onrender.com/api/scrape
```

## Features

- Rate limiting (60 requests per minute)
- Search functionality across job titles, companies, and skills
- Location-based filtering
- Automatic job scraping and updates
- Health check endpoint for monitoring
- CORS enabled for cross-origin requests

## Response Format

All endpoints return JSON responses with the following structure for jobs:

```json
{
    "id": integer,
    "job_title": string,
    "company_location": string,
    "salary": string,
    "job_type": string,
    "posted": string,
    "skills": string,
    "eligible_years": string,
    "apply_url": string,
    "company_logo": string,
    "created_at": datetime,
    "updated_at": datetime
}
```

## Rate Limiting

The API is rate-limited to 60 requests per minute per IP address. If you exceed this limit, you'll receive a 429 Too Many Requests response.

## Error Handling

The API uses standard HTTP status codes:
- 200: Success
- 400: Bad Request
- 404: Not Found
- 429: Too Many Requests
- 500: Internal Server Error

## Development

### Prerequisites
- Python 3.8+
- FastAPI
- SQLAlchemy
- PostgreSQL

### Installation
1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running Locally
```bash
uvicorn api:app --reload
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 