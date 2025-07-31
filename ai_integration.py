# ai_integration.py
import openai
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import config  # contains OPENAI_API_KEY

from user_data import USER_DATA_INTENT

# ✅ Set OpenAI key
openai.api_key = config.OPENAI_API_KEY

# ✅ Load the embedding model once
model = SentenceTransformer("all-MiniLM-L6-v2")

def load_resume_text(cv_path):
    try:
        with open(cv_path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return "Muhammad Yasir is an AI Engineer with 5 years experience in NLP, ML, and backend dev."  # Fallback summary


client = OpenAI(api_key=config.OPENAI_API_KEY)

def generate_openai_answer(question, resume_text=""):
    try:
        prompt = f"""
You are an AI job applicant filling out a job application form.
Here is your resume:\n{resume_text}\n
Answer the following question as truthfully and professionally as possible:
Q: {question}
A:"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert AI job applicant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ GPT fallback failed: {e}")
        return "N/A"
    
intent_entries = []
intent_values = []

for key, entry in USER_DATA_INTENT.items():
    if isinstance(entry, dict):  # ✅ Ensure it's a dict
        description = entry.get("description", "")
        value = entry.get("value", "")
        if description and value is not None:
            # Example entry: "FULL_NAME: Candidate's full name"
            intent_entries.append(f"{key.replace('_', ' ')}: {description}")
            intent_values.append(value)

# ✅ Main answer function
def get_dynamic_answer(question_text: str) -> str:
    question_text = question_text.strip()
    if not question_text:
        return "N/A"

    try:
        lowered = question_text.lower()

        # 📌 Static logic for critical matches
        if "street address" in lowered or "address line" in lowered:
            return USER_DATA_INTENT.get("STREET_ADDRESS", {}).get("value", "Islamabad")

        if "city" in lowered:
            return USER_DATA_INTENT.get("CURRENT_CITY", {}).get("value", "Islamabad")

        if "state" in lowered:
            return "Punjab"

        if "country" in lowered:
            return "Pakistan"

        if "notice" in lowered or "joining" in lowered or "availability" in lowered:
            return str(USER_DATA_INTENT.get("JOINING_DAYS", {}).get("value", "10"))

        if "hourly rate" in lowered:
            return str(USER_DATA_INTENT.get("EXPECTED_HOURLY_RATE", {}).get("value", "25"))

        if "how many" in lowered or "years of experience" in lowered or "lead" in lowered:
            return str(USER_DATA_INTENT.get("EXPERIENCE_YEARS", {}).get("value", "5"))

        if any(kw in lowered for kw in ["privacy policy", "agree to", "honesty", "accept", "terms"]):
            return "Yes"
        # 💰 Current Salary (Monthly)
        if "current" in lowered and "salary" in lowered:
            return str(USER_DATA_INTENT.get("CURRENT_SALARY", {}).get("value", "70000"))

        # 💰 Expected Salary (Monthly)
        if "expected" in lowered and "salary" in lowered and "month" in lowered:
            return str(USER_DATA_INTENT.get("EXPECTED_SALARY", {}).get("value", "90000"))

        # 💰 Expected Salary (Annual)
        if "expected" in lowered and "salary" in lowered and "year" in lowered:
            try:
                monthly = USER_DATA_INTENT.get("EXPECTED_SALARY", {}).get("value", 90000)
                yearly = int(monthly) * 12
                return str(yearly)
            except:
                return "1080000"  # Fallback



        # 🌍 Location match logic
        location_phrases = ["based in", "located in", "live in", "currently in", "reside in"]
        other_cities = ["karachi", "lahore", "peshawar", "multan", "us", "uae", "america", "dubai"]
        current_city = USER_DATA_INTENT.get("CURRENT_CITY", {}).get("value", "").lower()

        if any(phrase in lowered for phrase in location_phrases):
            for city in other_cities:
                if city in lowered and city not in current_city:
                    return "No"
            if current_city and current_city in lowered:
                return "Yes"

        # ✈️ Travel logic
        if any(kw in lowered for kw in [
            "travel onsite", "onsite role", "travel requirement", "willing to relocate",
            "relocate", "ok to travel", "comfortable with onsite", "on-site", "open to travel"
        ]):
            return "Yes"

        # 🤖 Try embedding-based match
        question_embedding = model.encode([question_text])
        similarities = cosine_similarity(question_embedding, intent_embeddings)[0]
        best_idx = int(np.argmax(similarities))
        best_score = similarities[best_idx]
        best_answer = intent_values[best_idx]
        best_match_text = intent_entries[best_idx]

        print(f"🔍 Matched: {best_match_text} → Score: {best_score:.2f} → Answer: {best_answer}")

        if best_score < 0.5 or best_answer == "N/A":
            print("🔁 Using GPT fallback...")
            resume_text = load_resume_text(USER_DATA_INTENT["CV_PATH"]["value"])
            gpt_answer = generate_openai_answer(question_text, resume_text)
            return gpt_answer

    except Exception as e:
        print(f"❌ Embedding logic error: {e}")
        return "N/A"
  
def get_ai_response(question, USER_DATA_INTENT):
    """Get AI response for general questions using OpenAI GPT-4"""

    try:
        # ✅ Dynamically build context from all fields in USER_DATA_INTENT
        context_lines = ["User Profile:"]
        for key, info in USER_DATA_INTENT.items():
            value = info.get('value', '')
            description = info.get('description', '')
            if value:
                formatted_key = key.replace('_', ' ').title()
                if description:
                    context_lines.append(f"{formatted_key}: {value} ({description})")
                else:
                    context_lines.append(f"{formatted_key}: {value}")
        context = "\n".join(context_lines)

        # Analyze the question
        question_lower = question.lower()

        # Prepare prompt based on question type
        if any(word in question_lower for word in ['how many', 'number of', 'years of experience', 'projects']):
            if 'full-stack' in question_lower and 'projects' in question_lower:
                prompt = f"""
                Based on this user profile, answer with ONLY A NUMBER for: {question}

                Context: {context}

                Return only a number (like 5, 10, 3.5) representing years or project count. No text, no words, just the number.
                """
            elif 'react' in question_lower and 'experience' in question_lower:
                prompt = f"""
                Based on this user profile, answer with ONLY A NUMBER for: {question}

                Context: {context}

                Return only a number representing years of React experience (like 3, 5, 2.5). No text, no words, just the number.
                """
            elif 'typescript' in question_lower and 'experience' in question_lower:
                prompt = f"""
                Based on this user profile, answer with ONLY A NUMBER for: {question}

                Context: {context}

                Return only a number representing years of TypeScript experience (like 2, 4, 3.5). No text, no words, just the number.
                """
            elif 'full-stack developer' in question_lower and 'experience' in question_lower:
                prompt = f"""
                Based on this user profile, answer with ONLY A NUMBER for: {question}

                Context: {context}

                Return only a number representing years of full-stack development experience (like 3, 5, 4.5). No text, no words, just the number.
                """
            else:
                prompt = f"""
                Based on this user profile, answer with ONLY A NUMBER for: {question}

                Context: {context}

                Return only a number. No text, no words, just the number.
                """
        else:
            prompt = f"""
            Based on this user profile, answer the following job application question in 1 concise sentence (max 15 words):

            Question: {question}

            Context: {context}

            Provide a professional, to-the-point answer suitable for a job application.
            """

        # Get OpenAI response
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional job application assistant. Provide concise, relevant answers."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3
        )

        answer = response.choices[0].message.content.strip()

        # For numeric questions, extract only the number
        if any(word in question_lower for word in ['how many', 'number of', 'years of experience', 'projects']):
            import re
            numbers = re.findall(r'\b\d+(?:\.\d+)?\b', answer)
            if numbers:
                return numbers[0]
            else:
                if 'react' in question_lower:
                    return "3"
                elif 'typescript' in question_lower:
                    return "2"
                elif 'full-stack' in question_lower:
                    return "5"
                else:
                    return "2"

        return answer

    except Exception as e:
        print(f"Error getting AI response: {e}")
        question_lower = question.lower()
        if 'how many' in question_lower or 'years' in question_lower:
            if 'react' in question_lower:
                return "3"
            elif 'typescript' in question_lower:
                return "2"
            elif 'full-stack' in question_lower:
                return "5"
            elif 'projects' in question_lower:
                return "8"
            else:
                return "3"
        return "Experienced professional seeking growth opportunities."

def get_smart_field_response(field_label, user_data):
    """Get smart response based on field label analysis"""
    label_lower = field_label.lower()

    # 🧮 Numeric field patterns
    if any(keyword in label_lower for keyword in ['full-stack projects']):
        return user_data.get('FULLSTACK_PROJECTS', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['ai projects']):
        return user_data.get('AI_PROJECTS', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['ml projects', 'machine learning projects']):
        return user_data.get('MACHINE_LEARNING_PROJECTS', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['web projects']):
        return user_data.get('WEB_PROJECTS', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['automation projects']):
        return user_data.get('AUTOMATION_PROJECTS', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['react experience']):
        return user_data.get('REACT_EXPERIENCE', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['typescript experience']):
        return user_data.get('TYPESCRIPT_EXPERIENCE', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['python experience']):
        return user_data.get('PYTHON_EXPERIENCE', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['js experience', 'javascript experience']):
        return user_data.get('JAVASCRIPT_EXPERIENCE', {}).get('value', 'N/A')
    elif 'experience' in label_lower and 'years' in label_lower:
        return user_data.get('EXPERIENCE_YEARS', {}).get('value', 'N/A')

    # ✅ Yes/No fields
    elif any(keyword in label_lower for keyword in ['figma']):
        return user_data.get('FIGMA_DESIGNS', {}).get('value', 'Yes')
    elif any(keyword in label_lower for keyword in ['portfolio']):
        return user_data.get('PORTFOLIO_AVAILABLE', {}).get('value', 'Yes')
    elif any(keyword in label_lower for keyword in ['github']):
        return user_data.get('GITHUB_AVAILABLE', {}).get('value', 'Yes')
    elif any(keyword in label_lower for keyword in ['chatgpt', 'ai experience']):
        return user_data.get('AI_CHATGPT_EXPERIENCE', {}).get('value', 'Yes')
    elif any(keyword in label_lower for keyword in ['coding assistant']):
        return user_data.get('CODING_ASSISTANT_EXPERIENCE', {}).get('value', 'Yes')
    elif any(keyword in label_lower for keyword in ['team']):
        return user_data.get('TEAM_COLLABORATION', {}).get('value', 'Yes')
    elif any(keyword in label_lower for keyword in ['agile']):
        return user_data.get('AGILE_EXPERIENCE', {}).get('value', 'Yes')
    elif any(keyword in label_lower for keyword in ['ci/cd']):
        return user_data.get('CI_CD_EXPERIENCE', {}).get('value', 'Yes')
    elif 'english' in label_lower and 'proficiency' in label_lower:
        return user_data.get('ENGLISH_PROFICIENCY', {}).get('value', 'Professional')


    # 🧠 Other fields via label match
    elif any(keyword in label_lower for keyword in ['name']):
        return user_data.get('FULL_NAME', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['email']):
        return user_data.get('EMAIL', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['phone']):
        return user_data.get('PHONE', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['linkedin']):
        return user_data.get('LINKEDIN', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['password']):
        return user_data.get('PASSWORD', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['cv', 'resume']):
        return user_data.get('CV_PATH', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['location']):
        return user_data.get('LOCATION', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['keyword']):
        return user_data.get('KEYWORD', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['current title', 'position']):
        return user_data.get('CURRENT_POSITION', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['company']):
        return user_data.get('CURRENT_COMPANY', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['duration']):
        return user_data.get('WORK_DURATION', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['master']):
        return user_data.get('EDUCATION_MASTERS', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['bachelor']):
        return user_data.get('EDUCATION_BACHELORS', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['summary']):
        return user_data.get('SUMMARY', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['key skills']):
        return user_data.get('KEY_SKILLS', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['languages']):
        return user_data.get('PROGRAMMING_LANGUAGES', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['frameworks']):
        return user_data.get('AI_FRAMEWORKS', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['databases']):
        return user_data.get('DATABASES', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['cloud']):
        return user_data.get('CLOUD_PLATFORMS', {}).get('value', 'N/A')
    elif any(keyword in label_lower for keyword in ['web technologies']):
        return user_data.get('WEB_TECHNOLOGIES', {}).get('value', 'N/A')

    # 🌐 Fallback to AI logic
    return get_ai_response(field_label, user_data)
