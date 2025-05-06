import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
from dotenv import load_dotenv
import socket
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = os.getenv('DB_PORT', '3306')

# Log database configuration (without password)
logger.info(f"Database configuration: host={DB_HOST}, port={DB_PORT}, user={DB_USER}, database={DB_NAME}")

# Validate required environment variables
required_vars = ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_NAME']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Test DNS resolution
try:
    logger.info(f"Testing DNS resolution for {DB_HOST}")
    ip_address = socket.gethostbyname(DB_HOST)
    logger.info(f"Successfully resolved {DB_HOST} to {ip_address}")
except socket.gaierror as e:
    logger.error(f"Failed to resolve hostname {DB_HOST}: {str(e)}")
    raise

# Create database URL
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Connection retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

for attempt in range(MAX_RETRIES):
    try:
        # Create engine with connection pool settings
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,  # Enable connection health checks
            connect_args={
                'connect_timeout': 10  # Add connection timeout
            }
        )
        
        # Test the connection
        with engine.connect() as conn:
            logger.info("Successfully connected to the database")
            break  # If successful, break the retry loop
            
    except Exception as e:
        logger.error(f"Attempt {attempt + 1}/{MAX_RETRIES} failed to connect to database: {str(e)}")
        if attempt < MAX_RETRIES - 1:
            logger.info(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
        else:
            logger.error("All connection attempts failed")
            raise

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 