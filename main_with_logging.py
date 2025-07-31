# main_with_logging.py
import time
import os
import random
import queue
from datetime import datetime

from utils import human_type
from config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD
from selenium_utils import (
    setup_driver,
    save_cookies,
    load_cookies
)
from job_application_flow import (
    search_jobs,
    click_first_job_and_easy_apply
)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from user_data import USER_DATA_INTENT

# Global log queue
log_queue = None

def log_to_ui(message):
    """Log message to UI queue and NOT the console."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    
    # This console print is removed to meet your requirement.
    # print(formatted_message) 
    
    if log_queue:
        try:
            log_queue.put(formatted_message)
        except Exception as e:
            # Fallback to console if queue fails
            print(f"UI LOGGING FAILED: {e}")

def login_to_linkedin():
    """Main function to handle LinkedIn login with cookies"""
    driver = setup_driver()
    
    try:
        log_to_ui("Opening LinkedIn...")
        driver.get("https://www.linkedin.com")
        time.sleep(3)
        
        cookies_file = "linkedin_cookies.pkl"
        if os.path.exists(cookies_file):
            log_to_ui("Cookies file found! Loading cookies...")
            load_cookies(driver, cookies_file)
            driver.refresh()
            time.sleep(3)
            
            if "feed" in driver.current_url or "mynetwork" in driver.current_url:
                log_to_ui("Successfully logged in with cookies!")
                return driver
            else:
                log_to_ui("Cookies didn't work. Proceeding with manual login...")
        
        log_to_ui("Proceeding with email/password login...")
        
        if "login" not in driver.current_url:
            driver.get("https://www.linkedin.com/login")
            time.sleep(3)
        
        log_to_ui("Entering email...")
        try:
            email_field = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "username"))
            )
            email_field.clear()
            time.sleep(0.5)
            human_type(email_field, LINKEDIN_EMAIL)
            log_to_ui("Email entered successfully!")
        except Exception as e:
            log_to_ui(f"Error finding email field: {str(e)}")
            try:
                email_field = driver.find_element(By.NAME, "session_key")
                email_field.clear()
                time.sleep(0.5)
                human_type(email_field, LINKEDIN_EMAIL)
                log_to_ui("Email entered with alternative selector!")
            except:
                log_to_ui("Could not find email field with any selector!")
                return None
        
        time.sleep(random.uniform(0.5, 1.0))
        
        log_to_ui("Entering password...")
        try:
            password_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "password"))
            )
            password_field.clear()
            time.sleep(0.5)
            human_type(password_field, LINKEDIN_PASSWORD)
            log_to_ui("Password entered successfully!")
        except Exception as e:
            log_to_ui(f"Error finding password field: {str(e)}")
            try:
                password_field = driver.find_element(By.NAME, "session_password")
                password_field.clear()
                time.sleep(0.5)
                human_type(password_field, LINKEDIN_PASSWORD)
                log_to_ui("Password entered with alternative selector!")
            except:
                log_to_ui("Could not find password field with any selector!")
                return None
        
        time.sleep(random.uniform(0.5, 1.0))
        
        log_to_ui("Clicking login button...")
        try:
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            login_button.click()
            log_to_ui("Login button clicked!")
        except Exception as e:
            log_to_ui(f"Error clicking login button: {str(e)}")
            try:
                login_button = driver.find_element(By.CSS_SELECTOR, "button[data-id='sign-in-form__submit-btn']")
                login_button.click()
                log_to_ui("Login button clicked with alternative selector!")
            except:
                try:
                    login_button = driver.find_element(By.CSS_SELECTOR, "button.btn__primary--large")
                    login_button.click()
                    log_to_ui("Login button clicked with CSS selector!")
                except:
                    log_to_ui("Could not find login button with any selector!")
                    return None
        
        log_to_ui("Waiting for login to complete...")
        time.sleep(5)
        
        current_url = driver.current_url
        log_to_ui(f"Current URL after login: {current_url}")
        
        if "feed" in current_url or "mynetwork" in current_url or "linkedin.com/in/" in current_url:
            log_to_ui("Login successful! Saving cookies...")
            save_cookies(driver, cookies_file)
        else:
            log_to_ui("Login might have failed or requires additional verification.")
            log_to_ui("Please check if there's a CAPTCHA or security challenge.")
        
        return driver
        
    except Exception as e:
        log_to_ui(f"Error during login: {str(e)}")
        if driver:
            driver.quit()
        return None

def run_linkedin_bot(ui_log_queue):
    """Main bot execution function that logs to UI"""
    global log_queue
    log_queue = ui_log_queue
    
    log_to_ui("🚀 Starting LinkedIn Auto Apply Bot...")
    log_to_ui("=" * 50)
    
    try:
        # Patch all modules to redirect their print statements to the UI
        import job_application_flow
        import ai_integration
        import selenium_utils
        import utils
        
        def patch_print_in_module(module):
            """Replaces the default print function in a module with our UI logger."""
            def ui_print_wrapper(*args, **kwargs):
                message = " ".join(str(arg) for arg in args)
                log_to_ui(message)
            
            # This is the 'monkey-patch' that does the replacement
            setattr(module, 'print', ui_print_wrapper)

        # Apply the patch to all relevant modules
        patch_print_in_module(job_application_flow)
        patch_print_in_module(ai_integration)
        patch_print_in_module(selenium_utils)
        patch_print_in_module(utils)
        
        driver = login_to_linkedin()
        
        if driver:
            log_to_ui("✅ Login completed! Now searching for jobs...")
            driver.get("https://www.linkedin.com/jobs")
            time.sleep(4)
            
            log_to_ui("🔍 Starting job search...")
            search_jobs(driver)
            
            log_to_ui("🎯 Now processing jobs with Easy Apply...")
            click_first_job_and_easy_apply(driver)
            
            log_to_ui("✅ Bot execution completed!")
            
        else:
            log_to_ui("❌ Failed to login. Please check your credentials.")
            
    except Exception as e:
        log_to_ui(f"❌ Bot error: {str(e)}")
    finally:
        log_to_ui("🛑 Bot session ended.")

# Direct execution for testing
if __name__ == "__main__":
    import queue
    test_queue = queue.Queue()
    run_linkedin_bot(test_queue)