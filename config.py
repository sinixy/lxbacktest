from os import getenv
from dotenv import load_dotenv

load_dotenv()

WORK_DIR = __path__
DATABENTO_API_KEY = getenv("DATABENTO_API_KEY")