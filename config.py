# ========================================
# USER CONFIGURATION - FILL THESE OUT
# ========================================

LINKEDIN_EMAIL = "abdulcui54455@gmail.com"
LINKEDIN_PASSWORD = "690854455"
JOB_SEARCH_KEYWORD = "python"
OPENAI_API_KEY = "sk-proj-*****" # Keep your API key secure

# File paths
USER_DATA_FILE = "data.txt"
COOKIES_FILE = "linkedin_cookies.pkl"
PDF_RESUME_PATH = "Yasir_s_Resume.pdf"
IMAGE_RESUME_PATH = "yasir-image-resume.jpg"

# Initialize OpenAI client - FIXED VERSION
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)