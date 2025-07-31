import streamlit as st 
import subprocess
import os
import json
import threading
import time
import queue
from datetime import datetime

# Initialize session state for logs
if 'log_queue' not in st.session_state:
    st.session_state.log_queue = queue.Queue()
if 'bot_process' not in st.session_state:
    st.session_state.bot_process = None
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False

st.set_page_config(page_title="LinkedIn Auto Apply Bot", layout="wide")
st.title("🤖 LinkedIn Auto Apply Bot")
st.markdown("Provide the folder path containing resume.pdf, data.txt, and optionally cookies.json.")

# Create two columns - left for controls, right for logs
col1, col2 = st.columns([1, 2])

with col1:
    st.header("📂 Configuration")
    
    # 📂 Folder input
    folder_path = st.text_input("📂 Enter Folder Path (e.g. D:/linkedin_bot_data)")

    resume_file_path = ""
    user_data = {}
    cookies = {}

    # 📄 Helper to parse data.txt into dict
    def parse_data_txt(file_path):
        data_dict = {}
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, value = line.split(":", 1)
                    data_dict[key.strip()] = value.strip()
        return data_dict

    # 🛠️ If folder is valid
    if folder_path and os.path.isdir(folder_path):
        resume_path = os.path.join(folder_path, "resume.pdf")
        data_path = os.path.join(folder_path, "data.txt")
        cookies_path = os.path.join(folder_path, "cookies.json")

        # ✅ Check for required files
        missing = []
        if not os.path.exists(resume_path):
            missing.append("resume.pdf")
        if not os.path.exists(data_path):
            missing.append("data.txt")

        if missing:
            st.error(f"Missing files: {', '.join(missing)}")
        else:
            # ✅ Parse user data from data.txt
            try:
                user_data = parse_data_txt(data_path)
                st.success("✅ Data files found!")
            except Exception as e:
                st.error(f"❌ Failed to parse data.txt: {e}")

            # 🔄 Load cookies if available
            if os.path.exists(cookies_path):
                with open(cookies_path, "r", encoding="utf-8") as f:
                    cookies = json.load(f)

            # 👇 Always show login fields (pre-fill from cookies if available)
            email = st.text_input("📧 Email", value=cookies.get("email", ""))
            password = st.text_input("🔒 Password", value=cookies.get("password", ""), type="password")
            keyword = st.text_input("💼 Job Keyword", value=cookies.get("keyword", ""), placeholder="e.g. Python Developer")
            location = st.text_input("📍 Location", value=cookies.get("location", ""), placeholder="e.g. Islamabad, Pakistan")

            # 💾 Save cookies.json
            if st.button("💾 Save Login Info"):
                if not all([email, password, keyword, location]):
                    st.error("⚠️ All fields are required to save login info.")
                else:
                    cookies = {
                        "email": email,
                        "password": password,
                        "keyword": keyword,
                        "location": location
                    }
                    with open(cookies_path, "w", encoding="utf-8") as f:
                        json.dump(cookies, f, indent=4)
                    st.success("✅ Login info saved to cookies.json")

            # Bot control buttons
            col_start, col_stop = st.columns(2)
            
            with col_start:
                if st.button("🚀 Start Bot", disabled=st.session_state.bot_running):
                    if not all([email, password, keyword, location, resume_path]):
                        st.warning("⚠️ Please fill in all login details and resume path.")
                    else:
                        user_data.update({
                            "EMAIL": email,
                            "PASSWORD": password,
                            "KEYWORD": keyword,
                            "LOCATION": location,
                            "CV_PATH": resume_path
                        })

                        # 📝 Write user_data.py
                        with open("user_data.py", "w", encoding="utf-8") as f:
                            f.write("USER_DATA_INTENT = " + json.dumps(user_data, indent=4))

                        st.success("✅ Bot starting...")
                        st.session_state.bot_running = True
                        
                        # Start bot in a separate thread
                        def run_bot(log_q):
                            from main_with_logging import run_linkedin_bot
                            # It uses the passed-in queue, not session_state
                            run_linkedin_bot(log_q)

                        # Pass the queue from session_state as an argument to the thread's target    
                        bot_thread = threading.Thread(
                            target=run_bot,
                            args=(st.session_state.log_queue,),  # The comma is important!
                            daemon=True
                        )
                        bot_thread.start()
                    
                           

            with col_stop:
                if st.button("⏹️ Stop Bot", disabled=not st.session_state.bot_running):
                    st.session_state.bot_running = False
                    st.warning("⚠️ Bot will stop after current job...")
                    st.rerun()

    else:
        st.info("⬆️ Please enter a valid folder path to begin.")

# Right column for logs
with col2:
    st.header("📋 Live Bot Logs")
    
    # Create placeholder for logs
    log_container = st.empty()
    
    # Display logs if bot is running
    if st.session_state.bot_running:
        # Auto-refresh every 2 seconds
        if st.button("🔄 Refresh Logs", key="refresh"):
            st.rerun()
        
        # Get all logs from queue
        logs = []
        try:
            while not st.session_state.log_queue.empty():
                log_entry = st.session_state.log_queue.get_nowait()
                logs.append(log_entry)
        except queue.Empty:
            pass
        
        # Store logs in session state to persist them
        if 'all_logs' not in st.session_state:
            st.session_state.all_logs = []
        
        st.session_state.all_logs.extend(logs)
        
        # Display all logs (limit to last 100 for performance)
        if st.session_state.all_logs:
            recent_logs = st.session_state.all_logs[-100:]
            log_text = "\n".join(recent_logs)
            
            with log_container.container():
                st.text_area(
                    "Bot Activity:", 
                    value=log_text,
                    height=500,
                    key="log_display"
                )
        
        # Auto-refresh every 2 seconds
        time.sleep(2)
        st.rerun()
    
    else:
        with log_container.container():
            st.info("🤖 Bot is not running. Click 'Start Bot' to begin and see live logs here.")
            
            # Show previous logs if any
            if 'all_logs' in st.session_state and st.session_state.all_logs:
                if st.button("📜 Show Previous Logs"):
                    recent_logs = st.session_state.all_logs[-50:]
                    log_text = "\n".join(recent_logs)
                    st.text_area("Previous Session Logs:", value=log_text, height=400)

# Status indicator
if st.session_state.bot_running:
    st.success("🟢 Bot is running...")
else:
    st.info("🔴 Bot is stopped")

# Auto-refresh the page every 3 seconds when bot is running
if st.session_state.bot_running:
    time.sleep(3)
    st.rerun()