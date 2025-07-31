# job_application_flow.py

import time
import random
import os

from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from config import JOB_SEARCH_KEYWORD

from utils import log_job_application
from user_data import USER_DATA_INTENT
from ai_integration import get_smart_field_response, get_dynamic_answer
from utils import human_type
from selenium_utils import (
    get_field_error_message,
    handle_dropdown_selection,
    handle_file_upload,
    get_field_label,
    validate_and_fix_fields,
    close_any_popup
)


def fill_field_with_data(driver, field_element, field_label, field_type, user_data):
    """Fill a field with appropriate data based on its label and type"""
    try:
        label_lower = field_label.lower()
        
        # Check for error messages first
        error_message = get_field_error_message(driver, field_element)
        if error_message:
            print(f"Error found for '{field_label}': {error_message}")
        
        # Get smart response based on field analysis
        if field_type == 'text_input' or field_type == 'textarea':
            # First try exact field mapping
            if any(keyword in label_lower for keyword in ['phone', 'mobile', 'number']):
                data = user_data.get('PHONE', '')
            elif any(keyword in label_lower for keyword in ['email', 'mail']):
                data = user_data.get('EMAIL', '')
            elif any(keyword in label_lower for keyword in ['name', 'full name', 'first name']):
                data = user_data.get('FULL_NAME', '')
            elif any(keyword in label_lower for keyword in ['linkedin', 'profile']):
                data = user_data.get('LINKEDIN', '')
            elif any(keyword in label_lower for keyword in ['company', 'current company']):
                data = user_data.get('CURRENT_COMPANY', '')
            elif any(keyword in label_lower for keyword in ['position', 'title', 'role']):
                data = user_data.get('CURRENT_POSITION', '')
            elif any(keyword in label_lower for keyword in ['education', 'degree', 'university']):
                data = user_data.get('EDUCATION_MASTERS', '')
            elif any(keyword in label_lower for keyword in ['skill', 'technologies']):
                data = user_data.get('KEY_SKILLS', '')
            elif any(keyword in label_lower for keyword in ['location', 'city', 'address', 'where']):
                data = user_data.get('LOCATION', '')
            else:
                # Use smart response for technical questions
                data = get_smart_field_response(field_label, user_data)
            
            # Fill the field
            if data:
                # Re-find element to avoid stale reference
                try:
                    field_element = driver.find_element(By.XPATH, f"//input[@aria-label='{field_label}'] | //input[@placeholder='{field_label}'] | //textarea[@aria-label='{field_label}']")
                except:
                    pass  # Use original element if re-finding fails
                
                field_element.clear()
                time.sleep(0.3)
                
                # Validate if field expects a number
                if any(keyword in label_lower for keyword in ['how many', 'years of experience', 'number of']):
                    # Extract number from data if it contains text
                    import re
                    numbers = re.findall(r'\b\d+(?:\.\d+)?\b', str(data))
                    if numbers:
                        data = numbers[0]
                    elif not data.replace('.', '').isdigit():
                        # Fallback to reasonable number
                        if 'react' in label_lower:
                            data = "3"
                        elif 'typescript' in label_lower:
                            data = "2"
                        elif 'full-stack' in label_lower:
                            data = "5"
                        else:
                            data = "3"
                
                human_type(field_element, str(data))
                print(f"Filled '{field_label}' with: {data}")
                
                # Trigger change event
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", field_element)
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", field_element)
                
            else:
                print(f"No data found for field: {field_label}")
                
        elif field_type == 'dropdown':
            handle_dropdown_selection(driver, field_element, field_label, user_data, error_message)
                
        elif field_type == 'file_upload':
            handle_file_upload(driver, field_element, field_label)
        
        time.sleep(0.5)
        
    except Exception as e:
        print(f"Error filling field '{field_label}': {e}")

def check_field_error(field):
    try:
        parent = field.find_element(By.XPATH, "..")  # move up to parent
        possible_msgs = parent.find_elements(By.XPATH, ".//div | .//span | .//p")

        for msg in possible_msgs:
            text = msg.text.strip().lower()
            if any(kw in text for kw in ["please", "required", "invalid", "enter", "must"]):
                print(f"⚠️ Field validation error detected → {text}")
                return text
    except:
        pass
    return None

# Check if any error messages are visible before proceeding
def has_form_errors(popup_container):
    try:
        errors = popup_container.find_elements(By.XPATH, ".//*[contains(text(), 'Please enter a valid answer') or contains(text(), 'required') or contains(text(),'must') or contains(text(),'invalid')]")
        for err in errors:
            if err.is_displayed():
                print(f"⚠️ Detected form error → {err.text.strip()}")
                return True
    except Exception as e:
        print(f"⚠️ Error checking for form errors: {e}")
    return False

def analyze_easy_apply_popup(driver):
    try:
        print("\n" + "=" * 50)
        print("EASY APPLY POPUP OPENED")
        print("=" * 50)

        time.sleep(2)

        selectors = [
            "div[role='dialog']",
            "div[class*='jobs-easy-apply']",
            "div[class*='artdeco-modal']",
            "div[aria-modal='true']"
        ]
        popup_container = None
        for selector in selectors:
            try:
                popup_container = driver.find_element(By.CSS_SELECTOR, selector)
                break
            except:
                continue

        if not popup_container:
            popup_container = driver.find_element(By.TAG_NAME, "body")
            
        required_fields = []

        print("Scanning form fields...")

        # --- 1. Radio buttons (fieldset) ---
        radio_groups = popup_container.find_elements(By.CSS_SELECTOR, "fieldset")
        for group in radio_groups:
            try:
                question = group.text.strip().split("\n")[0]
                answer = get_dynamic_answer(question)
        
                # Fallback if answer is N/A and only 2 options are available
                if (answer == "N/A" or not answer.strip()):
                    options = group.find_elements(By.CSS_SELECTOR, "label")
                    if len(options) == 2:
                        print(f"⚠️ No confident answer found. Guessing 'Yes' by default for: {question}")
                        answer = "Yes"
        
                print(f"→ Answering radio: {question} → {answer}")
        
                options = group.find_elements(By.CSS_SELECTOR, "label")
                for option in options:
                    if answer.lower() in option.text.lower():
                        try:
                            option.click()
                            time.sleep(random.uniform(0.5, 1.0))
                            break
                        except:
                            driver.execute_script("arguments[0].click();", option)
                            time.sleep(random.uniform(0.5, 1.0))
                            break
                        # 🔁 After clicking radio, check for error
                error = check_field_error(group)
                if error:
                    print(f"⚠️ Error detected after radio click: {error}")
                    print("↪ Retrying with fallback: 'Yes'")
                    for option in options:
                        if "yes" in option.text.lower():
                            option.click()
                            time.sleep(0.6)
                            break
            except Exception as e:
                print(f"⚠️ Radio group error: {e}")
                continue

        # --- 2. Input fields ---
        inputs = popup_container.find_elements(By.TAG_NAME, "input")
        for field in inputs:
            try:
                field_type = field.get_attribute("type")
                field_value = field.get_attribute("value") or ""
                required = field.get_attribute("required") or field.get_attribute("aria-required") == "true"

                if field_type in ['text', 'email', 'tel', 'number'] and required and not field_value.strip():
                    label = get_field_label(driver, field)
                    answer = get_dynamic_answer(label)
                    print(f"→ Filling input: {label} = {answer}")
                    field.clear()
                    field.send_keys(answer)
                    time.sleep(random.uniform(0.3, 0.6))
                                        # Check for error after filling
                    error = check_field_error(field)
                    if error:
                        print("⚠️ Retrying input due to error...")
                        fallback = "10" if "number" in error else "Yes"
                        field.clear()
                        field.send_keys(fallback)
            except Exception as e:
                print(f"⚠️ Input field error: {e}")

        # --- 3. Textareas ---
        textareas = popup_container.find_elements(By.TAG_NAME, "textarea")
        for field in textareas:
            try:
                if not field.get_attribute("value") and not field.text.strip():
                    label = get_field_label(driver, field)
                    answer = get_dynamic_answer(label)
                    print(f"→ Filling textarea: {label} = {answer}")
                    field.clear()
                    field.send_keys(answer)
                    time.sleep(random.uniform(0.3, 0.6))
            except Exception as e:
                print(f"⚠️ Textarea error: {e}")

      
        # --- 4. Dropdowns ---
        selects = popup_container.find_elements(By.TAG_NAME, "select")
        for select in selects:
            try:
                label = get_field_label(driver, select)
                answer = get_dynamic_answer(label)
        
                print(f"→ Dropdown: {label} → Suggested answer: {answer}")
        
                # Step 1: Scroll and click dropdown to load options
                driver.execute_script("arguments[0].scrollIntoView(true);", select)
                time.sleep(0.2)
                try:
                    select.click()
                except:
                    driver.execute_script("arguments[0].click();", select)
                time.sleep(0.5)  # allow options to render
        
                # Step 2: Extract options
                options = select.find_elements(By.TAG_NAME, "option")
                matched = False
        
                # Step 3: Match intelligently with answer
                for option in options:
                    option_text = option.text.strip().lower()
                    if answer.lower() in option_text:
                        option.click()
                        print(f"✅ Selected: {option.text}")
                        matched = True
                        time.sleep(0.3)
                        break
        
                # Step 4: Fallback logic (guess "Yes" if two options)
                if not matched and len(options) == 2:
                    for option in options:
                        if "yes" in option.text.lower():
                            option.click()
                            print("⚠️ No confident match. Selected 'Yes' by default.")
                            matched = True
                            break
        
                # Step 5: Final fallback — select second option
                if not matched and len(options) > 1:
                    options[1].click()
                    print("⚠️ Final fallback: Selected second option.")
                    time.sleep(0.3)
        
            except Exception as e:
                print(f"⚠️ Dropdown error: {e}")
                
                
      # --- 4B. Custom React-style Dropdowns ---
        custom_dropdowns = popup_container.find_elements(By.CSS_SELECTOR, "div[role='button'][aria-haspopup='listbox']")
        for dropdown in custom_dropdowns:
            try:
                label = get_field_label(driver, dropdown)
                answer = get_dynamic_answer(label)
                print(f"→ Custom Dropdown (React): {label} → Answer: {answer}")
        
                driver.execute_script("arguments[0].scrollIntoView(true);", dropdown)
                time.sleep(0.5)
        
                # Step 1: Click the dropdown
                try:
                    dropdown.click()
                except:
                    driver.execute_script("arguments[0].click();", dropdown)
                time.sleep(0.7)
        
                # Step 2: Wait and grab options
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='option'], li[role='option']"))
                )
                options = driver.find_elements(By.CSS_SELECTOR, "div[role='option'], li[role='option']")
        
                matched = False
                for option in options:
                    text = option.text.strip().lower()
                    if answer.lower() in text:
                        print(f"✅ Clicking: {option.text.strip()}")
                        driver.execute_script("arguments[0].scrollIntoView(true);", option)
                        option.click()
                        time.sleep(0.3)
                        matched = True
                        break
        
                # Step 3: Fallback to 'Yes' if nothing matched
                if not matched:
                    for option in options:
                        if "yes" in option.text.strip().lower():
                            option.click()
                            print("✅ Fallback selected: Yes")
                            time.sleep(0.3)
                            break
        
            except Exception as e:
                print(f"❌ Custom dropdown failed: {e}")


        # --- 5. File Uploads ---
        file_inputs = popup_container.find_elements(By.CSS_SELECTOR, "input[type='file']")
        for file_input in file_inputs:
            try:
                label = get_field_label(driver, file_input)
                resume_path = USER_DATA_INTENT.get("CV_PATH", "resume.pdf")
                file_input.send_keys(os.path.abspath(resume_path))
                time.sleep(1.5)
                print(f"→ Uploaded file: {resume_path}")
            except Exception as e:
                print(f"⚠️ File upload failed: {e}")
                
        # --- 6. Checkboxes (Privacy, Terms, etc.) ---
        checkboxes = popup_container.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        for checkbox in checkboxes:
            try:
                label = get_field_label(driver, checkbox).lower()
                if any(x in label for x in ["agree", "consent", "privacy", "accept", "confirm"]):
                    if not checkbox.is_selected():
                        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                        time.sleep(0.3)
                        checkbox.click()
                        print(f"✅ Checkbox clicked: {label}")
            except Exception as e:
                print(f"⚠️ Checkbox error: {e}")


       # --- Final step: Validate before Submit ---
            print("=" * 50)
            print("ALL FIELDS ATTEMPTED. VALIDATING BEFORE SUBMIT...")
            print("=" * 50)
            
            # Validate and fix any errors
            validate_and_fix_fields(driver, popup_container)
            
            # ✅ Final pre-submit check
            clicked = click_any_submit_button(driver, popup_container)
            if not clicked:
                print("⚠️ Submit button skipped due to incomplete dropdowns or failure.")
                return

            # Auto-submit after filling fields
            time.sleep(1)
            submit_application_and_handle_next_steps(driver)
            handle_exit_prompt(driver)

            
        else:
            print("All fields appear to be filled!")
        
        print("="*50)
        
    except Exception as e:
        print(f"Error analyzing popup: {str(e)}")

def submit_application_and_handle_next_steps(driver):
    """Submit the application and handle any follow-up popups or next steps"""
    try:
        print("\n" + "="*50)
        print("SUBMITTING APPLICATION")
        print("="*50)
        
        # Step 1: Check if Review button exists → click it first
        review_selectors = [
            "//button[contains(text(), 'Review')]",
            "//span[contains(text(), 'Review')]/ancestor::button"
        ]

        review_button = None
        for selector in review_selectors:
            try:
                review_button = WebDriverWait(driver, 4).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"🟡 Found Review button with selector: {selector}")
                driver.execute_script("arguments[0].scrollIntoView(true);", review_button)
                time.sleep(1)
                review_button.click()
                print("🟢 Clicked Review button")
                time.sleep(2)
                break
            except Exception as e:
                continue

        # Step 2: Now proceed with Submit/Continue/Next
        submit_selectors = [
            "button[aria-label*='Submit application']",
            "button[data-control-name*='continue_unify']",
            "//button[contains(text(), 'Submit application')]",
            "//button[contains(text(), 'Submit')]",
            "//button[contains(text(), 'Continue')]",
            "//button[contains(text(), 'Next')]",
            "button[class*='artdeco-button--primary']"
        ]

        submit_button = None

        for selector in submit_selectors:
            try:
                if selector.startswith("//"):
                    submit_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    submit_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                print(f"🟢 Found submit button with selector: {selector}")
                break
            except:
                continue

        if submit_button:
            print("Clicking submit button...")
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            time.sleep(1)
            submit_button.click()
            print("✅ Submit button clicked successfully!")
            time.sleep(3)


            return handle_application_flow(driver)
        else:
            print("❌ Could not find submit button!")
            return False

    except Exception as e:
        print(f"❌ Error submitting application: {e}")
        return False


def search_jobs(driver):
    """Search for jobs using the keyword"""
    try:
        print(f"Searching for jobs with keyword: {JOB_SEARCH_KEYWORD}")
        
        search_selectors = [
            "div[id='global-nav-search']",
            "div[class*='search-global-typeahead']",
            "button[aria-label*='Click to start a search']",
            "div[class='global-nav__search']",
            "input[placeholder*='Search']"
        ]
        
        search_element = None
        for selector in search_selectors:
            try:
                search_element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                print(f"Found search element with selector: {selector}")
                break
            except:
                continue
        
        if not search_element:
            print("Could not find search element, trying alternative approach...")
            driver.execute_script("document.querySelector('#global-nav-search').click();")
            time.sleep(2)
        else:
            print("Clicking search element...")
            driver.execute_script("arguments[0].click();", search_element)
            time.sleep(2)
        
        search_input_selectors = [
            "input[placeholder*='Search']",
            "input[aria-label*='Search']",
            "input[class*='search-global-typeahead__input']",
            "#global-nav-typeahead input",
            "input[type='text']"
        ]
        
        search_input = None
        for selector in search_input_selectors:
            try:
                search_input = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                print(f"Found search input with selector: {selector}")
                
                driver.execute_script("arguments[0].scrollIntoView(true);", search_input)
                time.sleep(1)
                
                try:
                    search_input.click()
                    time.sleep(0.5)
                except:
                    driver.execute_script("arguments[0].click();", search_input)
                    time.sleep(0.5)
                
                break
            except:
                continue
        
        if search_input:
            print("Typing job keyword...")
            try:
                search_input.clear()
                time.sleep(0.5)
                
                search_input.send_keys(JOB_SEARCH_KEYWORD)
                time.sleep(1)
                
                print("Keyword typed successfully!")
                
                search_input.send_keys('\n')
                
                print("Search completed!")
                time.sleep(3)
                
                click_jobs_filter(driver)
                apply_remote_filter(driver)
                
            except Exception as e:
                print(f"Error typing in search field: {e}")
                try:
                    driver.execute_script(f"arguments[0].value = '{JOB_SEARCH_KEYWORD}';", search_input)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", search_input)
                    time.sleep(1)
                    search_input.send_keys('\n')
                    print("Search completed with JavaScript!")
                    time.sleep(3)
                    
                    click_jobs_filter(driver)
                    apply_remote_filter(driver)
                    
                except Exception as e2:
                    print(f"Both typing methods failed: {e2}")
        else:
            print("Could not find search input field!")
        
    except Exception as e:
        print(f"Error during job search: {str(e)}")
        try:
            click_jobs_filter(driver)
            apply_remote_filter(driver)
        except:
            pass

def click_first_job_and_easy_apply(driver):
    """Click on first job and then click Easy Apply button"""
    try:
        print("Looking for first job in the list...")
        time.sleep(3)
        
        process_multiple_jobs(driver)
            
    except Exception as e:
        print(f"Error in job processing: {str(e)}")


def process_multiple_jobs(driver):
    """Process jobs in an infinite loop until jobs are exhausted or stopped manually."""
    try:
        job_index = 0

        print("\n" + "="*50)
        print(f"⚙️ STARTING INFINITE JOB APPLICATION LOOP")
        print("="*50)

        while True:
            print(f"\n>>> PROCESSING JOB {job_index + 1} <<<")

            job_selectors = [
                "div[data-job-id]",
                "li[data-job-id]", 
                "div[class*='job-card-container'][data-job-id]",
                "div[class*='jobs-search-results__list-item'] div[data-job-id]",
                "div[class*='job-card-list__entity-lockup']"
            ]

            available_jobs = []
            for selector in job_selectors:
                try:
                    jobs = driver.find_elements(By.CSS_SELECTOR, selector)
                    if jobs:
                        available_jobs = jobs
                        break
                except:
                    continue

            if job_index >= len(available_jobs):
                print("🔄 Reached end of job list. Scrolling for more jobs...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                continue

            target_job = available_jobs[job_index]
            easy_apply_found = False

            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", target_job)
                time.sleep(1)
                target_job.click()
                print(f"✅ Clicked on job {job_index + 1}")
                time.sleep(3)
            
                # 🔹 Extract job title
                try:
                    job_title_element = driver.find_element(By.CSS_SELECTOR, "h2[class*='job-details-jobs-unified-top-card__job-title']")
                    job_title = job_title_element.text.strip()
                except:
                    try:
                        job_title_element = driver.find_element(By.CSS_SELECTOR, "h1")
                        job_title = job_title_element.text.strip()
                    except:
                        job_title = f"Job #{job_index + 1}"
            
                # 🔹 Log job application immediately after click
                try:
                    print(f"📄 Job Title: {job_title}")
                    log_job_application(job_title, JOB_SEARCH_KEYWORD)
                except Exception as log_err:
                    print(f"⚠️ Failed to log job: {log_err}")


            except:
                print(f"❌ Failed to click job {job_index + 1}")
                job_index += 1
                continue

            # Step 1: Try clicking Easy Apply
            easy_apply_selectors = [
                "button[aria-label*='Easy Apply to']",
                "button[data-live-test*='jobs-apply-button']",
                "button[class*='jobs-apply-button']",
                "//button[contains(text(), 'Easy Apply')]"
            ]

            try:
                print("Checking if Easy Apply is visible right after opening job...")
                start_time = time.time()
                visible_easy_apply = None

                while time.time() - start_time < 2:
                    for selector in easy_apply_selectors:
                        try:
                            elements = driver.find_elements(By.XPATH, selector) if selector.startswith("//") else driver.find_elements(By.CSS_SELECTOR, selector)
                            for btn in elements:
                                if btn.is_displayed() and btn.is_enabled():
                                    visible_easy_apply = btn
                                    break
                            if visible_easy_apply:
                                break
                        except:
                            continue
                    if visible_easy_apply:
                        break
                    time.sleep(0.2)

                if visible_easy_apply:
                    print("🟢 Easy Apply is visible right after job open.")
                    driver.execute_script("arguments[0].scrollIntoView(true);", visible_easy_apply)
                    time.sleep(1)
                    visible_easy_apply.click()
                    print("✅ Easy Apply button clicked!")
                    easy_apply_found = True

            except Exception as e:
                print(f"⚠️ Step 1 Easy Apply check failed: {e}")

            # Step 2: If not found, wait for it
            if not easy_apply_found:
                print("Easy Apply not found immediately. Checking dropdown or waiting...")
                for selector in easy_apply_selectors:
                    try:
                        easy_apply_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector)) if selector.startswith("//") else EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        driver.execute_script("arguments[0].scrollIntoView(true);", easy_apply_btn)
                        time.sleep(1)
                        easy_apply_btn.click()
                        print("✅ Easy Apply button clicked after waiting.")
                        easy_apply_found = True
                        break
                    except:
                        continue

            # Step 3: If Easy Apply worked, proceed
            if easy_apply_found:
                time.sleep(3)
                analyze_easy_apply_popup(driver)
                application_success = handle_application_flow(driver)

                if application_success:
                    print(f"✅ Job {job_index + 1} application completed!")
                else:
                    print(f"❌ Job {job_index + 1} application failed")

                close_any_popup(driver)
                time.sleep(2)
            else:
                print(f"❌ No Easy Apply button for job {job_index + 1}. Skipping...")

            job_index += 1
            time.sleep(2)

    except Exception as e:
        print(f"❌ Error in infinite job processor: {e}")


def click_past_week_filter(driver):
    """Click on Past week option in Date posted filter"""
    try:
        print("Looking for Date posted Past week option...")
        
        past_week_selectors = [
            "label[for*='advanced-filter-timePostedRange-r604800']",
            "//label[contains(text(), 'Past week')]",
            "//span[contains(text(), 'Past week')]/../..//input[@type='radio']",
            "//span[contains(text(), 'Past week')]/../..//label",
            "input[value='r604800'][name*='timePostedRange']"
        ]
        
        past_week_option = None
        
        for selector in past_week_selectors:
            try:
                if selector.startswith("//"):
                    past_week_option = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    past_week_option = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                print(f"Found Past week option with selector: {selector}")
                break
            except:
                continue
        
        if not past_week_option:
            try:
                labels = driver.find_elements(By.TAG_NAME, "label")
                for label in labels:
                    if "Past week" in label.text:
                        for_attr = label.get_attribute("for")
                        if for_attr:
                            try:
                                past_week_option = driver.find_element(By.ID, for_attr)
                                print("Found Past week radio by label association")
                                break
                            except:
                                continue
                        else:
                            try:
                                past_week_option = label.find_element(By.XPATH, ".//input[@type='radio']")
                                print("Found Past week radio in label")
                                break
                            except:
                                try:
                                    past_week_option = label.find_element(By.XPATH, "..//input[@type='radio']")
                                    print("Found Past week radio near label")
                                    break
                                except:
                                    continue
                
                if not past_week_option:
                    for label in labels:
                        if "Past week" in label.text:
                            past_week_option = label
                            print("Will click Past week label directly")
                            break
            except:
                pass
        
        if past_week_option:
            print("Clicking Past week filter option...")
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", past_week_option)
            time.sleep(1)
            
            click_success = False
            try:
                past_week_option.click()
                print("Past week clicked with direct click")
                click_success = True
            except Exception as e1:
                print(f"Direct click failed: {e1}")
                try:
                    driver.execute_script("arguments[0].click();", past_week_option)
                    print("Past week clicked with JavaScript")
                    click_success = True
                except Exception as e2:
                    print(f"JavaScript click failed: {e2}")
                    try:
                        actions = ActionChains(driver)
                        actions.move_to_element(past_week_option).click().perform()
                        print("Past week clicked with ActionChains")
                        click_success = True
                    except Exception as e3:
                        print(f"All Past week click methods failed: {e1}, {e2}, {e3}")
            
            if click_success:
                print("Past week filter selected successfully!")
                time.sleep(1)
            else:
                print("Failed to click Past week option!")
                
        else:
            print("Could not find Past week filter option!")
            
    except Exception as e:
        print(f"Error clicking Past week filter: {str(e)}")

def click_easy_apply_filter(driver):
    """Click on Easy Apply filter button"""
    try:
        print("Looking for Easy Apply filter button...")
        
        easy_apply_button = None
        
        try:
            easy_apply_button = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Easy Apply')]"))
            )
            print("Found Easy Apply button using XPath")
        except:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, "button[class*='search-reusables__filter-pill-button']")
                for button in buttons:
                    if "Easy Apply" in button.text:
                        easy_apply_button = button
                        print("Found Easy Apply button by text search")
                        break
            except:
                pass
        
        if easy_apply_button:
            print("Clicking Easy Apply filter button...")
            driver.execute_script("arguments[0].scrollIntoView(true);", easy_apply_button)
            time.sleep(0.5)
            easy_apply_button.click()
            print("Easy Apply filter applied successfully!")
            time.sleep(2)
        else:
            print("Could not find Easy Apply filter button!")
            
    except Exception as e:
        print(f"Error clicking Easy Apply filter: {str(e)}")

def click_show_results(driver):
    """Click on Show results button after applying filters"""
    try:
        print("Looking for Show results button...")
        
        show_results_selectors = [
            "button[data-test='reusables-filters-modal-show-results-button']",
            "button[aria-label*='Apply current filters to show']",
            "//button[contains(text(), 'Show results')]",
            "//button[contains(text(), 'Apply')]",
            "button[class*='search-reusables-filters-show-results-button']",
            "button[class*='artdeco-button--primary']"
        ]
        
        show_results_button = None
        
        for selector in show_results_selectors:
            try:
                if selector.startswith("//"):
                    show_results_button = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    show_results_button = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                print(f"Found Show results button with selector: {selector}")
                break
            except:
                continue
        
        if not show_results_button:
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for button in buttons:
                    button_text = button.text.strip().lower()
                    if "show results" in button_text or "apply" in button_text:
                        show_results_button = button
                        print("Found Show results button by text search")
                        break
            except:
                pass
        
        if show_results_button:
            print("Clicking Show results button...")
            driver.execute_script("arguments[0].scrollIntoView(true);", show_results_button)
            time.sleep(0.5)
            show_results_button.click()
            print("Show results button clicked successfully!")
            time.sleep(3)
            
            click_easy_apply_filter(driver)
            
        else:
            print("Could not find Show results button!")
            
    except Exception as e:
        print(f"Error clicking Show results button: {str(e)}")

def apply_remote_filter(driver):
    """Click on All filters button and select Remote option"""
    try:
        print("Looking for All filters button...")
        
        all_filters_selectors = [
            "button[aria-label='Show all filters. Clicking this button displays all available filter options.']",
            "button[class*='search-reusables__all-filters-pill-button']",
            "//button[contains(text(), 'All filters')]",
            "button[class*='artdeco-pill'][class*='filter-pill-button']"
        ]
        
        all_filters_button = None
        
        for selector in all_filters_selectors:
            try:
                if selector.startswith("//"):
                    all_filters_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    all_filters_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                print(f"Found All filters button with selector: {selector}")
                break
            except:
                continue
        
        if not all_filters_button:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, "button[class*='filter-pill-button']")
                for button in buttons:
                    if "All filters" in button.text or "filters" in button.text.lower():
                        all_filters_button = button
                        print("Found All filters button by text search")
                        break
            except:
                pass
        
        if all_filters_button:
            print("Clicking All filters button...")
            driver.execute_script("arguments[0].scrollIntoView(true);", all_filters_button)
            time.sleep(0.5)
            all_filters_button.click()
            time.sleep(3)
            
            click_past_week_filter(driver)
            
            print("Looking for Remote filter option...")
            
            remote_selectors = [
                "//label[contains(text(), 'Remote')]",
                "//label[contains(text(), 'Remote')]//input[@type='checkbox']",
                "//span[contains(text(), 'Remote')]/../..//input[@type='checkbox']",
                "//span[contains(text(), 'Remote')]/../..//label",
                "label[for*='workplaceType-2']",
                "input[value='2'][name*='workplaceType']"
            ]
            
            remote_option = None
            
            for selector in remote_selectors:
                try:
                    if selector.startswith("//"):
                        remote_option = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        remote_option = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    print(f"Found Remote option with selector: {selector}")
                    break
                except:
                    continue
            
            if not remote_option:
                try:
                    labels = driver.find_elements(By.TAG_NAME, "label")
                    for label in labels:
                        if "Remote" in label.text:
                            for_attr = label.get_attribute("for")
                            if for_attr:
                                try:
                                    remote_option = driver.find_element(By.ID, for_attr)
                                    print("Found Remote checkbox by label association")
                                    break
                                except:
                                    continue
                            else:
                                try:
                                    remote_option = label.find_element(By.XPATH, ".//input[@type='checkbox']")
                                    print("Found Remote checkbox in label")
                                    break
                                except:
                                    try:
                                        remote_option = label.find_element(By.XPATH, "..//input[@type='checkbox']")
                                        print("Found Remote checkbox near label")
                                        break
                                    except:
                                        continue
                    
                    if not remote_option:
                        for label in labels:
                            if "Remote" in label.text:
                                remote_option = label
                                print("Will click Remote label directly")
                                break
                except:
                    pass
            
            if remote_option:
                print("Clicking Remote filter option...")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", remote_option)
                time.sleep(1)
                
                click_success = False
                try:
                    remote_option.click()
                    print("Remote clicked with direct click")
                    click_success = True
                except Exception as e1:
                    print(f"Direct click failed: {e1}")
                    try:
                        driver.execute_script("arguments[0].click();", remote_option)
                        print("Remote clicked with JavaScript")
                        click_success = True
                    except Exception as e2:
                        print(f"JavaScript click failed: {e2}")
                        try:
                            actions = ActionChains(driver)
                            actions.move_to_element(remote_option).click().perform()
                            print("Remote clicked with ActionChains")
                            click_success = True
                        except Exception as e3:
                            print(f"ActionChains click failed: {e3}")
                            try:
                                driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));", remote_option)
                                print("Remote clicked with dispatch event")
                                click_success = True
                            except Exception as e4:
                                print(f"All click methods failed: {e1}, {e2}, {e3}, {e4}")
                
                if click_success:
                    print("Remote filter selected successfully!")
                    time.sleep(1)
                    click_show_results(driver)
                else:
                    print("Failed to click Remote option!")
                    
            else:
                print("Could not find Remote filter option!")
                
        else:
            print("Could not find All filters button!")
            
    except Exception as e:
        print(f"Error applying remote filter: {str(e)}")

def click_jobs_filter(driver):
    """Click on Jobs filter button"""
    try:
        print("Looking for Jobs filter button...")
        
        jobs_button = None
        
        try:
            jobs_button = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Jobs')]"))
            )
            print("Found Jobs button using XPath")
        except:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, "button[class*='search-reusables__filter-pill-button']")
                for button in buttons:
                    if "Jobs" in button.text:
                        jobs_button = button
                        print("Found Jobs button by text search")
                        break
            except:
                pass
        
        if jobs_button:
            print("Clicking Jobs filter button...")
            driver.execute_script("arguments[0].scrollIntoView(true);", jobs_button)
            time.sleep(0.5)
            jobs_button.click()
            print("Jobs filter applied successfully!")
            time.sleep(2)
        else:
            print("Could not find Jobs filter button!")
            
    except Exception as e:
        print(f"Error clicking Jobs filter: {str(e)}")

def handle_application_flow(driver):
    """Handle the complete application flow including multiple popups"""
    max_steps = 10
    step_count = 0
    
    while step_count < max_steps:
        step_count += 1
        print(f"\n--- Application Step {step_count} ---")
        
        time.sleep(2)
        
        if is_application_completed(driver):
            print("Application completed successfully!")
            return True
        
        if has_popup_with_fields(driver):
            print("Found another popup with fields to fill...")
            analyze_easy_apply_popup(driver)
            
            if not submit_application_and_handle_next_steps(driver):
                print("Failed to submit this step")
                break
        else:
            if not click_any_submit_button(driver):
                print("No more submit buttons found")
                break
    
    print("Application flow completed or max steps reached")
    return True

def is_application_completed(driver):
    """Check if the application process is completed"""
    try:
        completion_indicators = [
            "//text()[contains(., 'Application sent')]",
            "//text()[contains(., 'Your application was sent')]",
            "//text()[contains(., 'Application submitted')]",
            "//text()[contains(., 'Thank you')]",
            "//text()[contains(., 'We have received')]",
            "div[class*='artdeco-inline-feedback'][class*='success']",
            "div[class*='jobs-apply-confirmation']"
        ]
        
        for indicator in completion_indicators:
            try:
                if indicator.startswith("//text()"):
                    element = driver.find_element(By.XPATH, indicator)
                else:
                    element = driver.find_element(By.CSS_SELECTOR, indicator)
                if element:
                    return True
            except:
                continue
                
        return False
        
    except Exception as e:
        return False

def has_popup_with_fields(driver):
    """Check if there's a popup with form fields that need filling"""
    try:
        popup_selectors = [
            "div[role='dialog']",
            "div[class*='jobs-easy-apply']",
            "div[class*='artdeco-modal']",
            "div[aria-modal='true']"
        ]
        
        for selector in popup_selectors:
            try:
                popup = driver.find_element(By.CSS_SELECTOR, selector)
                empty_inputs = popup.find_elements(By.CSS_SELECTOR, "input[type='text']:not([value]), input[type='email']:not([value]), textarea:empty")
                if empty_inputs:
                    return True
            except:
                continue
        
        return False
        
    except Exception as e:
        return False

def click_any_submit_button(driver, popup_container=None):
    """
    Click any available submit/continue/next button,
    but first check if required dropdowns are still unfilled.
    """

    try:
        # Optional: pass popup_container to scan dropdowns
        if popup_container:
            # --- 1. Standard dropdowns ---
            selects = popup_container.find_elements(By.TAG_NAME, "select")
            for select in selects:
                selected = select.get_attribute("value") or ""
                if not selected.strip():
                    print("⚠️ Skipping submit: a standard dropdown is unfilled.")
                    return False

            # --- 2. Custom React-style dropdowns ---
            react_dropdowns = popup_container.find_elements(By.CSS_SELECTOR, "div[role='button'][aria-haspopup='listbox']")
            for dropdown in react_dropdowns:
                current_value = dropdown.text.strip()
                if current_value in ["Select an option", "", None]:
                    print("⚠️ Skipping submit: a custom dropdown is still unselected.")
                    return False

        # --- Proceed to submit buttons ---
        submit_selectors = [
            "button[aria-label*='Submit']",
            "button[aria-label*='Continue']",
            "button[aria-label*='Next']",
            "//button[contains(text(), 'Submit')]",
            "//button[contains(text(), 'Continue')]",
            "//button[contains(text(), 'Next')]",
            "//button[contains(text(), 'Send')]",
            "button[class*='artdeco-button--primary']"
        ]

        for selector in submit_selectors:
            try:
                if selector.startswith("//"):
                    button = driver.find_element(By.XPATH, selector)
                else:
                    button = driver.find_element(By.CSS_SELECTOR, selector)

                if button.is_enabled() and button.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(1)
                    button.click()
                    print(f"✅ Clicked button: {button.text.strip() or '[Unnamed Button]'}")
                    time.sleep(2)
                    return True
            except:
                continue

        return False

    except Exception as e:
        print(f"❌ Error in click_any_submit_button: {e}")
        return False

def handle_exit_prompt(driver):
    try:
        print("🔍 Checking for Save/Discard exit popup...")

        popup = driver.find_element(By.XPATH, "//div[contains(@class, 'artdeco-modal')]")
        if not popup:
            return

        text = popup.text.lower()
        if "save application" in text or "you haven’t finished" in text:
            print("🛑 Exit prompt detected!")

            # Try to find and click radio button
            options = popup.find_elements(By.CSS_SELECTOR, "label")

            for option in options:
                label = option.text.lower()
                if "discard" in label:
                    print("❌ Discarding incomplete application")
                    option.click()
                    break
                elif "save" in label:
                    print("💾 Saving filled application")
                    option.click()
                    break

            # Now find and click the confirm button
            confirm_button = popup.find_element(By.XPATH, ".//button[contains(text(), 'Submit') or contains(text(), 'Save')]")
            if confirm_button:
                confirm_button.click()
                print("✅ Exit prompt resolved.")

        time.sleep(1)

    except Exception as e:
        print(f"⚠️ Could not handle save/discard popup: {e}")
