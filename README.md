# HirePro Jobs API

A FastAPI-based jobs API that scrapes and serves job listings from talentd.in.

## Project Structure

```
.
├── api.py           # FastAPI application
├── config.py        # Database configuration
├── models.py        # SQLAlchemy models
├── scraper.py       # Job scraper
├── requirements.txt # Project dependencies
└── Procfile        # Deployment configuration
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize the database:
```python
from models import Base
from config import engine
Base.metadata.create_all(bind=engine)
```

3. Run the scraper to populate the database:
```bash
python scraper.py
```

4. Start the API server:
```bash
python api.py
```

## API Endpoints

- `GET /api/jobs?source={source}&search={search}&location={location}`
  - Get jobs filtered by source (Regular/Freshers/Internships), search term, and location
- `GET /api/jobs/{job_id}`
  - Get a specific job by ID

## Database Configuration

The application uses MySQL hosted on InfinityFree:
- Host: sql303.infinityfree.com
- Database: if0_38916982_hirepro
- Username: if0_38916982
- Password: T32XK4YpNOErX

## Deployment

The application is configured for deployment with a Procfile. It can be deployed to platforms like:
- Heroku
- PythonAnywhere
- Render 