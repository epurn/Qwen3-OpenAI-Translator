import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create a logger for the application
logger = logging.getLogger(__name__)