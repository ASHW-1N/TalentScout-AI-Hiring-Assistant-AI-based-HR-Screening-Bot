# TalentScout AI Hiring Assistant 🤖



An intelligent chatbot for initial candidate screening, powered by LLaMA3 and Streamlit. This AI assistant conducts technical interviews, evaluates candidates, and generates detailed reports.

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![Groq](https://img.shields.io/badge/Groq-00A67E?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)

## ✨ Features

- **Smart Interview Flow**  
  ![Interview Flow GIF](https://via.placeholder.com/600x300/2563eb/ffffff?text=Interview+Flow+Demo)
  - Multi-stage conversation (info collection → HR questions → technical evaluation)
  - Context-aware question generation
  - Dynamic difficulty based on experience level

- **Technical Assessment**  
  ![Tech Questions](https://via.placeholder.com/300x200/2563eb/ffffff?text=Tech+Questions)
  - Generates 3-5 questions per technology
  - Includes scenario-based questions
  - Covers both theory and practical knowledge

- **Comprehensive Evaluation**  
  ![Evaluation Report](https://via.placeholder.com/300x200/2563eb/ffffff?text=Evaluation+Report)
  - Scores technical competence (70%)
  - Assesses communication skills (20%)
  - Evaluates cultural fit (10%)
  - Generates PDF/JSON reports

## 🏗️ Project Architecture

```mermaid
graph TD
    A[Streamlit UI] --> B[Session State]
    B --> C[Information Collection]
    C --> D[HR Questions]
    D --> E[Technical Assessment]
    E --> F[Evaluation Engine]
    F --> G[Report Generation]
    G --> H[PDF/JSON Output]
    C -->|Groq API| I[LLaMA3-70B]
    D --> I
    E --> I
    F --> I

talent-scout/
├── main.py                  # Main application logic
├── README.md                # Project documentation
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
├── candidates/              # Generated reports storage
│   ├── {name}_report.json   # JSON candidate reports
│   └── {name}_report.pdf    # PDF candidate reports
└── hr_interview_questions_dataset.json  # HR questions database
