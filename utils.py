import os
import time
import random
from openai import OpenAI
import config

# Initialize OpenAI client
client = OpenAI(api_key=config.OPENAI_API_KEY)

def load_user_data():
    """Load user data from data.txt file"""
    data = {}
    try:
        with open("data.txt", "r", encoding="utf-8") as file:
            for line in file:
                if ":" in line:
                    key, value = line.strip().split(":", 1)
                    data[key.strip()] = value.strip()
        print("User data loaded successfully!")
        return data
    except FileNotFoundError:
        print("data.txt file not found!")
        return {}
    except Exception as e:
        print(f"Error loading user data: {e}")
        return {}

# Load user data at startup
USER_DATA = load_user_data()

def human_type(element, text):
    """Type text like a human with random delays between characters"""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.02, 0.08))

import csv

def log_job_application(job_title, search_keyword, filename="applied_jobs.csv"):
    file_exists = os.path.exists(filename)
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Job Title', 'Search Keyword'])
        writer.writerow([job_title, search_keyword])
    print(f"✅ Data saved to CSV: {filename}")
