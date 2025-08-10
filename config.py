import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    
    # Common database settings
    DATABASE_NAME = os.environ.get('DATABASE_NAME') or 'projectFlow'
    
    # PostgreSQL configuration
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST') or 'localhost'
    POSTGRES_PORT = int(os.environ.get('POSTGRES_PORT') or 5432)
    POSTGRES_USER = os.environ.get('POSTGRES_USER') or 'postgres'
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD') or '123'
    
    # MySQL configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT') or 3306)
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or ''
    
    # Will be set dynamically based on available database
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_TYPE = None

def check_postgresql_connection():
    """Check if PostgreSQL is available and accessible"""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        connection = psycopg2.connect(
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT,
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            database='postgres',
            connect_timeout=5  # 5 second timeout
        )
        connection.close()
        return True
    except ImportError:
        logger.warning("psycopg2 not installed. Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed: {e}")
        return False

def check_mysql_connection():
    """Check if MySQL is available and accessible"""
    try:
        import pymysql
        
        connection = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            connect_timeout=5  # 5 second timeout
        )
        connection.close()
        return True
    except ImportError:
        logger.warning("pymysql not installed. Install with: pip install pymysql")
        return False
    except Exception as e:
        logger.warning(f"MySQL connection failed: {e}")
        return False

def create_postgresql_database():
    """Create PostgreSQL database if it doesn't exist"""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        connection = psycopg2.connect(
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT,
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            database='postgres'
        )
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
                (Config.DATABASE_NAME,)
            )
            exists = cursor.fetchone()
            
            if not exists:
                cursor.execute(f'CREATE DATABASE "{Config.DATABASE_NAME}"')
                logger.info(f"PostgreSQL database '{Config.DATABASE_NAME}' created successfully.")
            else:
                logger.info(f"PostgreSQL database '{Config.DATABASE_NAME}' already exists.")
                
        connection.close()
        return True
        
    except Exception as e:
        logger.error(f"Error creating PostgreSQL database: {e}")
        return False

def create_mysql_database():
    """Create MySQL database if it doesn't exist"""
    try:
        import pymysql
        
        connection = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD
        )
        
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DATABASE_NAME}`;")
            connection.commit()
            logger.info(f"MySQL database '{Config.DATABASE_NAME}' ensured to exist.")
            
        connection.close()
        return True
        
    except Exception as e:
        logger.error(f"Error creating MySQL database: {e}")
        return False

def setup_database():
    """
    Automatically detect and configure the available database.
    Priority: PostgreSQL > MySQL
    """
    
    # Force a specific database type if environment variable is set
    force_db = os.environ.get('FORCE_DATABASE_TYPE', '').lower()
    
    if force_db == 'postgresql':
        logger.info("Forcing PostgreSQL usage...")
        if check_postgresql_connection() and create_postgresql_database():
            Config.SQLALCHEMY_DATABASE_URI = (
                f"postgresql+psycopg2://{Config.POSTGRES_USER}:{Config.POSTGRES_PASSWORD}"
                f"@{Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}/{Config.DATABASE_NAME}"
            )
            Config.DATABASE_TYPE = 'postgresql'
            logger.info("Using PostgreSQL database")
            return True
        else:
            logger.error("Failed to connect to PostgreSQL as requested")
            return False
    
    elif force_db == 'mysql':
        logger.info("Forcing MySQL usage...")
        if check_mysql_connection() and create_mysql_database():
            Config.SQLALCHEMY_DATABASE_URI = (
                f"mysql+pymysql://{Config.MYSQL_USER}:{Config.MYSQL_PASSWORD}"
                f"@{Config.MYSQL_HOST}:{Config.MYSQL_PORT}/{Config.DATABASE_NAME}"
            )
            Config.DATABASE_TYPE = 'mysql'
            logger.info("Using MySQL database")
            return True
        else:
            logger.error("Failed to connect to MySQL as requested")
            return False
    
    # Auto-detect available database (PostgreSQL first, then MySQL)
    logger.info("Auto-detecting available database...")
    
    # Try PostgreSQL first
    if check_postgresql_connection():
        logger.info("PostgreSQL is available, attempting to use it...")
        if create_postgresql_database():
            Config.SQLALCHEMY_DATABASE_URI = (
                f"postgresql+psycopg2://{Config.POSTGRES_USER}:{Config.POSTGRES_PASSWORD}"
                f"@{Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}/{Config.DATABASE_NAME}"
            )
            Config.DATABASE_TYPE = 'postgresql'
            logger.info("Successfully configured PostgreSQL database")
            return True
    
    # Try MySQL as fallback
    if check_mysql_connection():
        logger.info("MySQL is available, attempting to use it...")
        if create_mysql_database():
            Config.SQLALCHEMY_DATABASE_URI = (
                f"mysql+pymysql://{Config.MYSQL_USER}:{Config.MYSQL_PASSWORD}"
                f"@{Config.MYSQL_HOST}:{Config.MYSQL_PORT}/{Config.DATABASE_NAME}"
            )
            Config.DATABASE_TYPE = 'mysql'
            logger.info("Successfully configured MySQL database")
            return True
    
    # No database available
    logger.error("No database connection available! Please check your database servers and credentials.")
    logger.error("Make sure either PostgreSQL or MySQL is running and accessible.")
    return False

# Run database setup at startup
if not setup_database():
    raise RuntimeError("Failed to configure any database connection!")