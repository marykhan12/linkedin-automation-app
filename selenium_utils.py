import os
import pickle 
import time
import re
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from utils import human_type

from config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD

def setup_driver():
    
    """Setup Chrome driver with optimized options"""
    chrome_options = Options()
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    print("Starting Chrome browser...")
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    print("Chrome browser started successfully!")
    return driver

def save_cookies(driver, filename="linkedin_cookies.pkl"):
    """Save cookies to file"""
    with open(filename, 'wb') as file:
        pickle.dump(driver.get_cookies(), file)
    print("Cookies saved successfully!")

def load_cookies(driver, filename="linkedin_cookies.pkl"):
    """Load cookies from file"""
    try:
        with open(filename, 'rb') as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        print("Cookies loaded successfully!")
        return True
    except FileNotFoundError:
        print("No cookies file found. Will need to login manually.")
        return False

def get_field_label(driver, field_element):
    """Get the label text for a form field by checking various label patterns"""
    try:
        # Method 1: Check for aria-label
        aria_label = field_element.get_attribute("aria-label")
        if aria_label and aria_label.strip():
            return aria_label.strip()
        
        # Method 2: Check for placeholder
        placeholder = field_element.get_attribute("placeholder")
        if placeholder and placeholder.strip():
            return placeholder.strip()
        
        # Method 3: Look for associated label by ID
        field_id = field_element.get_attribute("id")
        if field_id:
            try:
                label_element = driver.find_element(By.CSS_SELECTOR, f"label[for='{field_id}']")
                if label_element.text.strip():
                    return label_element.text.strip()
            except:
                pass
        
        # Method 4: Look for label in parent or nearby elements
        try:
            parent = field_element.find_element(By.XPATH, "./..")
            labels = parent.find_elements(By.TAG_NAME, "label")
            for label in labels:
                if label.text.strip():
                    return label.text.strip()
        except:
            pass
        
        # Method 5: Look for text in preceding sibling elements
        try:
            preceding_elements = field_element.find_elements(By.XPATH, "./preceding-sibling::*")
            for element in reversed(preceding_elements):
                text = element.text.strip()
                if text and len(text) < 200 and '?' in text:  # Questions usually end with ?
                    return text
        except:
            pass
        
        # Method 6: Look for nearby text elements
        try:
            parent = field_element.find_element(By.XPATH, "./..")
            text_elements = parent.find_elements(By.CSS_SELECTOR, "span, div, p, h1, h2, h3, h4, h5, h6")
            for element in text_elements:
                text = element.text.strip()
                if text and len(text) < 200 and ('?' in text or 'experience' in text.lower()):
                    return text
        except:
            pass
        
        return "Unknown field"
        
    except Exception as e:
        return "Unknown field"

def get_field_error_message(driver, field_element):
    """Get error message for a field if any exists"""
    try:
        error_selectors = [
            ".//following-sibling::*[contains(@class, 'error')]",
            ".//following-sibling::*[contains(@class, 'invalid')]",
            ".//following-sibling::*[contains(text(), 'Please')]",
            ".//following-sibling::*[contains(text(), 'Enter')]",
            ".//following-sibling::*[contains(text(), 'Select')]",
            ".//following-sibling::*[contains(text(), 'Required')]",
            ".//parent::*//*[contains(@class, 'error')]",
            ".//parent::*//*[contains(@class, 'invalid')]",
            ".//parent::*//*[contains(text(), 'Please')]",
            ".//parent::*//*[contains(text(), 'Enter')]"
        ]
        
        for selector in error_selectors:
            try:
                error_element = field_element.find_element(By.XPATH, selector)
                error_text = error_element.text.strip()
                if error_text and len(error_text) < 200:
                    return error_text
            except:
                continue
        
        return None
        
    except Exception as e:
        return None

def handle_file_upload(driver, field_element, field_label):
    """Handle file upload fields"""
    try:
        field_accept = field_element.get_attribute("accept")
        
        if field_accept and "pdf" in field_accept.lower():
            resume_path = os.path.join(os.getcwd(), "Yasir_s_Resume.pdf")
            if os.path.exists(resume_path):
                field_element.send_keys(resume_path)
                print(f"Uploaded PDF resume for: {field_label}")
            else:
                print(f"PDF resume file not found: {resume_path}")
        elif field_accept and any(img_type in field_accept.lower() for img_type in ["jpg", "jpeg", "png", "image"]):
            image_resume_path = os.path.join(os.getcwd(), "yasir-image-resume.jpg")
            if os.path.exists(image_resume_path):
                field_element.send_keys(image_resume_path)
                print(f"Uploaded image resume for: {field_label}")
            else:
                print(f"Image resume file not found: {image_resume_path}")
        else:
            # Default to PDF
            resume_path = os.path.join(os.getcwd(), "Yasir_s_Resume.pdf")
            if os.path.exists(resume_path):
                field_element.send_keys(resume_path)
                print(f"Uploaded default PDF resume for: {field_label}")
            else:
                print(f"No resume file found for: {field_label}")
    except Exception as e:
        print(f"Error uploading file for '{field_label}': {e}")

def handle_dropdown_selection(driver, dropdown_element, field_label, user_data, error_message=None):
    """Handle dropdown field selection intelligently"""
    try:
        label_lower = field_label.lower()
        
        # Handle Select elements
        if dropdown_element.tag_name == "select":
            select = Select(dropdown_element)
            
            # Get all options
            options = select.options
            selected_option = None
            
            # Determine what to select based on field type
            if "figma" in label_lower or "high-fidelity" in label_lower:
                for option in options:
                    if option.text.lower() in ["yes", "true"]:
                        selected_option = option
                        break
            elif "english" in label_lower or "proficiency" in label_lower:
                for option in options:
                    option_text = option.text.lower()
                    if any(level in option_text for level in ["native", "fluent", "advanced", "professional"]):
                        selected_option = option
                        break
            elif "experience" in label_lower and "years" in label_lower:
                exp_years = user_data.get('EXPERIENCE_YEARS', '5').replace('+', '').strip()
                for option in options:
                    if exp_years in option.text:
                        selected_option = option
                        break
            
            # Select the option
            if selected_option:
                select.select_by_visible_text(selected_option.text)
                print(f"Selected '{selected_option.text}' for '{field_label}'")
            else:
                # Select first non-empty option
                for option in options:
                    if option.text.strip() and "select" not in option.text.lower():
                        select.select_by_visible_text(option.text)
                        print(f"Selected default '{option.text}' for '{field_label}'")
                        break
        else:
            # Handle custom dropdowns
            dropdown_element.click()
            time.sleep(1)
            
            # Look for dropdown options
            try:
                options = driver.find_elements(By.CSS_SELECTOR, "[role='option'], .dropdown-option, li")
                for option in options:
                    option_text = option.text.lower()
                    if "figma" in label_lower and "yes" in option_text:
                        option.click()
                        print(f"Selected '{option.text}' for '{field_label}'")
                        return
                    elif option_text and "select" not in option_text:
                        option.click()
                        print(f"Selected '{option.text}' for '{field_label}'")
                        return
            except:
                pass
        
    except Exception as e:
        print(f"Error handling dropdown '{field_label}': {e}")

def validate_and_fix_fields(driver, popup_container):
    """Validate all fields and fix any errors found"""
    try:
        print("\n--- VALIDATING AND FIXING FIELDS ---")
        
        # Look for all error messages
        error_selectors = [
            "*[contains(@class, 'error')]",
            "*[contains(@class, 'invalid')]", 
            "*[contains(text(), 'Please make a selection')]",
            "*[contains(text(), 'Please enter a valid')]",
            "*[contains(text(), 'Enter a decimal number')]",
            "*[style*='color: red']",
            "*[style*='color:red']"
        ]
        
        errors_found = []
        for selector in error_selectors:
            try:
                error_elements = popup_container.find_elements(By.XPATH, f".//{selector}")
                for error_element in error_elements:
                    error_text = error_element.text.strip()
                    if error_text and len(error_text) < 200:
                        errors_found.append(error_text)
                        print(f"Error found: {error_text}")
            except:
                continue
        
        if errors_found:
            print(f"Total errors found: {len(errors_found)}")
            
            # Find and fix fields with decimal number errors
            for error in errors_found:
                if "decimal number" in error.lower():
                    # Find numeric input fields and fix them
                    try:
                        numeric_inputs = popup_container.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='number']")
                        for input_field in numeric_inputs:
                            current_value = input_field.get_attribute('value')
                            if current_value and not current_value.replace('.', '').isdigit():
                                # Extract numbers from the current value
                                import re
                                numbers = re.findall(r'\b\d+(?:\.\d+)?\b', current_value)
                                if numbers:
                                    input_field.clear()
                                    time.sleep(0.2)
                                    input_field.send_keys(numbers[0])
                                    print(f"Fixed numeric field with value: {numbers[0]}")
                                    driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", input_field)
                    except Exception as e:
                        print(f"Error fixing numeric fields: {e}")
            
            # Re-analyze popup if there were errors
            time.sleep(1)
            analyze_easy_apply_popup(driver)
        else:
            print("No validation errors found!")
            
    except Exception as e:
        print(f"Error during validation: {e}")

def login_to_linkedin():
    """Main function to handle LinkedIn login with cookies"""
    driver = setup_driver()
    
    try:
        print("Opening LinkedIn...")
        driver.get("https://www.linkedin.com")
        time.sleep(3)
        
        cookies_file = "linkedin_cookies.pkl"
        if os.path.exists(cookies_file):
            print("Cookies file found! Loading cookies...")
            load_cookies(driver, cookies_file)
            driver.refresh()
            time.sleep(3)
            
            if "feed" in driver.current_url or "mynetwork" in driver.current_url:
                print("Successfully logged in with cookies!")
                return driver
            else:
                print("Cookies didn't work. Proceeding with manual login...")
        
        print("Proceeding with email/password login...")
        
        if "login" not in driver.current_url:
            driver.get("https://www.linkedin.com/login")
            time.sleep(3)
        
        print("Entering email...")
        try:
            email_field = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "username"))
            )
            email_field.clear()
            time.sleep(0.5)
            human_type(email_field, LINKEDIN_EMAIL)
            print("Email entered successfully!")
        except Exception as e:
            print(f"Error finding email field: {str(e)}")
            try:
                email_field = driver.find_element(By.NAME, "session_key")
                email_field.clear()
                time.sleep(0.5)
                human_type(email_field, LINKEDIN_EMAIL)
                print("Email entered with alternative selector!")
            except:
                print("Could not find email field with any selector!")
                return None
        
        time.sleep(random.uniform(0.5, 1.0))
        
        print("Entering password...")
        try:
            password_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "password"))
            )
            password_field.clear()
            time.sleep(0.5)
            human_type(password_field, LINKEDIN_PASSWORD)
            print("Password entered successfully!")
        except Exception as e:
            print(f"Error finding password field: {str(e)}")
            try:
                password_field = driver.find_element(By.NAME, "session_password")
                password_field.clear()
                time.sleep(0.5)
                human_type(password_field, LINKEDIN_PASSWORD)
                print("Password entered with alternative selector!")
            except:
                print("Could not find password field with any selector!")
                return None
        
        time.sleep(random.uniform(0.5, 1.0))
        
        print("Clicking login button...")
        try:
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            login_button.click()
            print("Login button clicked!")
        except Exception as e:
            print(f"Error clicking login button: {str(e)}")
            try:
                login_button = driver.find_element(By.CSS_SELECTOR, "button[data-id='sign-in-form__submit-btn']")
                login_button.click()
                print("Login button clicked with alternative selector!")
            except:
                try:
                    login_button = driver.find_element(By.CSS_SELECTOR, "button.btn__primary--large")
                    login_button.click()
                    print("Login button clicked with CSS selector!")
                except:
                    print("Could not find login button with any selector!")
                    return None
        
        print("Waiting for login to complete...")
        time.sleep(5)
        
        current_url = driver.current_url
        print(f"Current URL after login: {current_url}")
        
        if "feed" in current_url or "mynetwork" in current_url or "linkedin.com/in/" in current_url:
            print("Login successful! Saving cookies...")
            save_cookies(driver, cookies_file)
        else:
            print("Login might have failed or requires additional verification.")
            print("Please check if there's a CAPTCHA or security challenge.")
            input("If you see any security challenges, complete them and press Enter to continue...")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "global-nav-search")))

        return driver
        
    except Exception as e:
        print(f"Error during login: {str(e)}")
        print("Keeping browser open for manual debugging...")
        input("Press Enter to close browser after checking the issue...")
        driver.quit()
        return None

def close_any_popup(driver):
    """Close any remaining popups or modals"""
    try:
        close_selectors = [
            "button[aria-label*='Dismiss']",
            "button[aria-label*='Close']",
            "//button[contains(@aria-label, 'Close')]",
            "//button[contains(@aria-label, 'Dismiss')]",
            "button[class*='artdeco-modal__dismiss']",
            "svg[class*='close-icon']/..",
            "[data-test-modal-close-btn]"
        ]
        
        for selector in close_selectors:
            try:
                if selector.startswith("//"):
                    close_btn = driver.find_element(By.XPATH, selector)
                else:
                    close_btn = driver.find_element(By.CSS_SELECTOR, selector)
                
                if close_btn.is_displayed():
                    close_btn.click()
                    print("Closed popup/modal")
                    time.sleep(1)
                    return True
            except:
                continue
        
        return False
        
    except Exception as e:
        return False

