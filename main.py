import streamlit as st
import json
import re
import random
import os
import time
import textwrap
from groq import Groq
from datetime import datetime
from dotenv import load_dotenv
from fpdf import FPDF  # For PDF generation

# Load environment variables
load_dotenv()

# Initialize Groq client
try:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
except:
    st.error("GROQ_API_KEY not found. Please create a .env file with your Groq API key.")
    st.stop()

# Load HR questions dataset
try:
    with open('hr_interview_questions_dataset.json', 'r') as f:
        hr_questions = json.load(f)
except Exception as e:
    st.error(f"Failed to load HR questions dataset: {str(e)}")
    st.stop()

# Define system roles with enhanced prompts
SYSTEM_ROLES = {
    "screening": (
        "You're an experienced HR screening assistant for TalentScout. Conduct initial candidate screenings by:"
        "\n1. Collecting essential candidate information professionally"
        "\n2. Asking relevant HR questions from the provided dataset"
        "\n3. Maintaining friendly yet professional tone"
        "\n4. Validating inputs where necessary"
        "\n\nAlways maintain context and conversation flow."
    ),
    "technical": (
        "Generate technical interview questions based on these rules:"
        "\n- Create 3-5 questions per technology"
        "\n- Questions should assess practical knowledge"
        "\n- Include 1 scenario-based question per technology"
        "\n- Difficulty should match candidate's experience level"
        "\n- Cover both theoretical and practical aspects"
    ),
    "evaluation": (
        "Evaluate candidates based on:"
        "\n1. Technical competence (70% weight)"
        "\n2. Communication skills (20% weight)"
        "\n3. Cultural fit (10% weight)"
        "\n\nProvide:"
        "\n- Strengths and weaknesses"
        "\n- Recommendation (Strong Yes/Yes/No/Strong No)"
        "\n- Justification for recommendation"
        "\n- Suggested next steps"
    )
}

# Initialize session state
def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Welcome to TalentScout! I'm your AI Hiring Assistant. " 
             "I'll conduct an initial screening to assess your fit for technical roles. "
             "Let's begin with some basic information. You can type 'exit' anytime to end the session."},
            {"role": "assistant", "content": "May I have your full name?"}
        ]
    
    defaults = {
        "stage": "collect_info",
        "candidate_data": {
            "name": "",
            "email": "",
            "phone": "",
            "position": "",
            "experience": "",
            "location": "",
            "tech_stack": [],
            "responses": {},
            "evaluation": "",
            "screening_result": ""
        },
        "current_question": "",
        "tech_questions": {},
        "questions_asked": 0,
        "start_time": time.time(),
        "input_key": 0  # Key to reset the input field
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Validate input formats
def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

def is_valid_phone(phone):
    pattern = r"^\+?[1-9]\d{1,14}$"
    return re.match(pattern, phone) is not None

def is_valid_experience(exp):
    try:
        years = int(''.join(filter(str.isdigit, exp)))
        return years >= 0
    except:
        return False

# Generate response using LLaMA3 with enhanced prompting
def generate_response(prompt, role_description, temperature=0.3, max_tokens=1024):
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": role_description},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stop=None
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"API Error: {str(e)}"

# Get relevant HR questions with experience matching
def get_hr_questions(position, experience):
    try:
        exp_num = int(''.join(filter(str.isdigit, experience or "0")))
        level = "Entry" if exp_num < 3 else "Mid" if exp_num < 6 else "Senior"
        
        filtered = [
            q for q in hr_questions 
            if (position.lower() in q["role"].lower() or 
                "General" in q["role"]) and 
            level in q.get("experience", "")
        ]
        
        return random.sample(filtered, min(3, len(filtered))) if filtered else []
    except:
        return random.sample(hr_questions, 3)

# Generate technical questions with context awareness
def generate_tech_questions(tech_stack, experience):
    if not tech_stack:
        return {}
    
    questions = {}
    for tech in tech_stack[:5]:
        prompt = f"""
        Candidate Profile:
        - Technology: {tech}
        - Experience: {experience} years
        
        Generate 3-5 technical questions that:
        1. Assess core concepts
        2. Include one real-world scenario
        3. Cover best practices
        4. Match {experience} years experience level
        
        Return only the questions, one per line.
        """
        response = generate_response(prompt, SYSTEM_ROLES["technical"])
        # Clean response by removing numbers
        clean_questions = [re.sub(r'^\d+[\.\)]\s*', '', q).strip() 
                          for q in response.split("\n") if q.strip()]
        questions[tech] = clean_questions[:5]  # Limit to 5 questions
    
    return questions

# Evaluate candidate with detailed analysis
def evaluate_candidate():
    candidate = st.session_state.candidate_data
    responses = "\n".join([f"Q: {q}\nA: {a}" for q, a in candidate['responses'].items()])
    
    prompt = f"""
    **Candidate Evaluation**
    Position: {candidate['position']}
    Experience: {candidate['experience']} years
    Tech Stack: {', '.join(candidate['tech_stack'])}
    
    **Interview Responses:**
    {responses}
    
    **Evaluation Criteria:**
    - Technical Competence (70%)
    - Communication Skills (20%)
    - Cultural Fit (10%)
    
    Provide:
    1. Overall assessment (1-10 rating)
    2. Key strengths and weaknesses
    3. Recommendation (Strong Yes/Yes/No/Strong No)
    4. Detailed justification
    5. Suggested next steps
    """
    
    evaluation = generate_response(prompt, SYSTEM_ROLES["evaluation"])
    return evaluation

# Save candidate data securely
def save_candidate_data():
    candidate = st.session_state.candidate_data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create candidates directory
    os.makedirs("candidates", exist_ok=True)
    
    # Save JSON file
    json_filename = f"candidates/{candidate['name']}_{timestamp}.json".replace(" ", "_")
    with open(json_filename, "w") as f:
        json.dump(candidate, f, indent=2)
    
    # Generate PDF report
    pdf_filename = f"candidates/{candidate['name']}_{timestamp}.pdf".replace(" ", "_")
    generate_pdf_report(candidate, pdf_filename)
    
    return json_filename, pdf_filename

# Generate PDF report
def generate_pdf_report(candidate, filename):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.cell(0, 10, 'TalentScout Candidate Report', 0, 1, 'C')
            self.ln(10)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
            
        def chapter_title(self, title):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, title, 0, 1)
            self.ln(4)
            
        def chapter_body(self, body):
            self.set_font('Arial', '', 10)
            # Wrap text to fit within page width
            lines = textwrap.wrap(body, width=100)
            for line in lines:
                self.cell(0, 5, line, 0, 1)
            self.ln(8)
            
        def add_section(self, title, content):
            self.chapter_title(title)
            self.chapter_body(content)

    pdf = PDF()
    pdf.add_page()
    
    # Candidate Information
    info = (
        f"Name: {candidate['name']}\n"
        f"Email: {candidate['email']}\n"
        f"Phone: {candidate['phone']}\n"
        f"Position: {candidate['position']}\n"
        f"Experience: {candidate['experience']} years\n"
        f"Location: {candidate['location']}\n"
        f"Tech Stack: {', '.join(candidate['tech_stack'])}"
    )
    pdf.add_section("Candidate Information", info)
    
    # Interview Responses
    responses = "\n\n".join([f"Q: {q}\nA: {a}" for q, a in candidate['responses'].items()])
    pdf.add_section("Interview Responses", responses)
    
    # Evaluation
    pdf.add_section("Evaluation", candidate['evaluation'])
    
    # Screening Result
    pdf.add_section("Screening Result", candidate['screening_result'])
    
    # Save PDF
    pdf.output(filename)

# Streamlit app with enhanced UI
def main():
    st.set_page_config(
        page_title="TalentScout AI Hiring Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS to fix input position
    st.markdown("""
    <style>
    /* Always show chat input at bottom */
    .stChatInput {
        position: fixed !important;
        bottom: 20px !important;
        width: calc(100% - 3rem) !important;
        left: 1.5rem !important;
        z-index: 100;
    }
    
    /* Chat message container */
    .stChatMessageContainer {
        padding-bottom: 80px !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: #f0f2f6;
        padding: 1rem;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #4CAF50 !important;
        color: white !important;
        margin-bottom: 5px;
    }
    
    .report-btn {
        background-color: #2196F3 !important;
    }
    
    /* Progress indicators */
    .progress-item {
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("TalentScout AI Hiring Assistant 🤖")
    st.caption("Intelligent Candidate Screening System | AI/ML Intern Assignment")
    
    # Initialize session
    init_session_state()
    
    # Create two columns - main chat and sidebar
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Create a container for chat messages
        chat_container = st.container()
        
        with chat_container:
            # Display chat messages with avatars
            for msg in st.session_state.messages:
                avatar = "🤖" if msg["role"] == "assistant" else "👤"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])
    
    # Always show the chat input at the bottom
    prompt = st.chat_input("Type your response...", key=f"input_{st.session_state.input_key}")
    
    if prompt:
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.input_key += 1  # Reset input field
        
        # Check for exit commands
        if prompt.lower() in ["exit", "quit", "bye", "goodbye", "stop", "end"]:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Thank you for your time. Your information has been saved. We'll contact you about next steps."
            })
            save_candidate_data()
            st.session_state.stage = "complete"
            st.rerun()
        
        # Process based on current stage
        candidate = st.session_state.candidate_data
        
        if st.session_state.stage == "collect_info":
            if not candidate["name"]:
                candidate["name"] = prompt
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "What's your professional email address?"
                })
            elif not candidate["email"]:
                if is_valid_email(prompt):
                    candidate["email"] = prompt
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "Please share your phone number (international format: +[country code][number])"
                    })
                else:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "⚠️ Please enter a valid email address (e.g., name@company.com)"
                    })
            elif not candidate["phone"]:
                if is_valid_phone(prompt):
                    candidate["phone"] = prompt
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "What specific position are you applying for?"
                    })
                else:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "⚠️ Please enter a valid phone number (e.g., +1234567890)"
                    })
            elif not candidate["position"]:
                candidate["position"] = prompt
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "How many years of relevant experience do you have in this field?"
                })
            elif not candidate["experience"]:
                if is_valid_experience(prompt):
                    candidate["experience"] = prompt
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "Where are you currently located (city, country)?"
                    })
                else:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "⚠️ Please enter valid years of experience (e.g., 3)"
                    })
            elif not candidate["location"]:
                candidate["location"] = prompt
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Please list your technical skills (comma-separated):"
                })
            elif not candidate["tech_stack"]:
                candidate["tech_stack"] = [t.strip() for t in prompt.split(",") if t.strip()]
                st.session_state.stage = "hr_questions"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Great! Let's start with some general questions."
                })
        
        elif st.session_state.stage == "hr_questions":
            if st.session_state.current_question:
                # Save response to current question
                candidate["responses"][st.session_state.current_question] = prompt
                st.session_state.current_question = ""
            
            # Ask next question if available
            if st.session_state.questions_asked < 3:
                position = st.session_state.candidate_data["position"]
                experience = st.session_state.candidate_data["experience"]
                selected_questions = get_hr_questions(position, experience)
                
                if selected_questions:
                    question = random.choice(selected_questions)
                    st.session_state.current_question = question["question"]
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": st.session_state.current_question
                    })
                    st.session_state.questions_asked += 1
                else:
                    st.session_state.stage = "tech_questions"
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": "Now let's move to technical questions."
                    })
            else:
                st.session_state.stage = "tech_questions"
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "Now let's move to technical questions."
                })
        
        elif st.session_state.stage == "tech_questions":
            if st.session_state.current_question:
                # Save response to current technical question
                candidate["responses"][st.session_state.current_question] = prompt
                st.session_state.current_question = ""
            
            # Generate tech questions if not already generated
            if not st.session_state.tech_questions:
                tech_stack = st.session_state.candidate_data["tech_stack"]
                st.session_state.tech_questions = generate_tech_questions(
                    tech_stack, 
                    st.session_state.candidate_data["experience"]
                )
                st.session_state.tech_queue = [
                    (tech, q) 
                    for tech, questions in st.session_state.tech_questions.items() 
                    for q in questions
                ]
                random.shuffle(st.session_state.tech_queue)
            
            # Ask next technical question if available
            if st.session_state.tech_queue:
                tech, question = st.session_state.tech_queue.pop(0)
                st.session_state.current_question = f"**{tech}**: {question}"
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": st.session_state.current_question
                })
            else:
                st.session_state.stage = "evaluation"
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "Thank you for your responses! I'm now evaluating your answers..."
                })
        
        elif st.session_state.stage == "evaluation":
            # Perform evaluation
            with st.spinner("Analyzing responses and generating evaluation..."):
                evaluation = evaluate_candidate()
                st.session_state.candidate_data["evaluation"] = evaluation
                
                # Generate screening decision
                decision_prompt = f"""
                Based on this evaluation:
                {evaluation}
                
                Provide a final screening decision in this format:
                Recommendation: [Strong Yes/Yes/No/Strong No]
                Confidence: [High/Medium/Low]
                Summary: [One-sentence summary]
                """
                decision = generate_response(decision_prompt, SYSTEM_ROLES["evaluation"])
                st.session_state.candidate_data["screening_result"] = decision
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"## Evaluation Complete\n\n{evaluation}\n\n**Decision**:\n{decision}"
                })
                
                # Save data and show next steps
                json_filename, pdf_filename = save_candidate_data()
                st.session_state.candidate_data["report_path"] = pdf_filename
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": (
                        "Thank you for completing the screening! Your information has been securely stored. "
                        "Our recruitment team will contact you about next steps within 3 business days. "
                        "You can now close this window."
                    )
                })
                st.session_state.stage = "complete"
        
        # Rerun to update UI
        st.rerun()
    
    with col2:
        # Sidebar content
        st.header("Screening Progress")
        stages = {
            "collect_info": "Information Gathering",
            "hr_questions": "HR Questions",
            "tech_questions": "Technical Assessment",
            "evaluation": "Evaluation",
            "complete": "Complete"
        }
        
        current_index = list(stages.keys()).index(st.session_state.stage) if st.session_state.stage in stages else 0
        for i, (key, label) in enumerate(stages.items()):
            status = "✅" if i < current_index else "➡️" if i == current_index else "◻️"
            st.markdown(f"<div class='progress-item'>{status} {label}</div>", unsafe_allow_html=True)
        
        if st.session_state.stage != "greeting":
            elapsed = int(time.time() - st.session_state.start_time)
            st.caption(f"Elapsed time: {elapsed//60}m {elapsed%60}s")
            
            if st.session_state.candidate_data["name"]:
                st.divider()
                st.subheader("Candidate Summary")
                st.write(f"**Name**: {st.session_state.candidate_data['name']}")
                st.write(f"**Position**: {st.session_state.candidate_data['position']}")
                st.write(f"**Experience**: {st.session_state.candidate_data['experience']} years")
                st.write(f"**Tech Stack**: {', '.join(st.session_state.candidate_data['tech_stack'][:3])}{'...' if len(st.session_state.candidate_data['tech_stack']) > 3 else ''}")
                
                if st.session_state.stage == "complete":
                    st.success("Screening completed!")
                    
                    # Download buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            "Download JSON Report",
                            data=json.dumps(st.session_state.candidate_data, indent=2),
                            file_name=f"{st.session_state.candidate_data['name']}_report.json",
                            mime="application/json"
                        )
                    
                    with col2:
                        # Read PDF file content
                        pdf_path = st.session_state.candidate_data.get("report_path", "")
                        if pdf_path and os.path.exists(pdf_path):
                            with open(pdf_path, "rb") as f:
                                pdf_data = f.read()
                            st.download_button(
                                "Download PDF Report",
                                data=pdf_data,
                                file_name=os.path.basename(pdf_path),
                                mime="application/pdf",
                                key="pdf_download"
                            )

# Run the app
if __name__ == "__main__":
    main()
