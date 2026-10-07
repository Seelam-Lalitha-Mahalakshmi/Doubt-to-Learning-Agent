# 🧠 CogniLearn — AI-Powered Doubt-to-Learning Agent

An intelligent, pedagogical cognitive tutoring platform designed to transform a student's academic doubts across multiple subjects into personalized, deep-understanding learning experiences.

---

## 🌟 Key Features

1. **Multi-Subject Cognitive Diagnostic Engine**:
   - Ingests academic questions, equations, and code across **Mathematics, Physics, Chemistry, Computer Science, Biology, and General Sciences**.
   - Accurately diagnoses the underlying scientific concept and identifies the student's root **learning gap or misconception**.
   - Outlines essential **prerequisites** required to solidify understanding.

2. **Personalized Explanation Studio**:
   - Adapts explanations to the student's chosen academic level: **Beginner (ELI5/Intuitive)**, **Intermediate (High School/Standard)**, or **Advanced (College/Rigorous)**.
   - **Mental Model & Analogy Generator**: Connects abstract theoretical laws to real-world intuitive analogies.
   - **Step-by-Step Conceptual Breakdown**: First-principles breakdown with LaTeX equations rendered via KaTeX.
   - **Common Pitfalls & Myth Busters**: Warns students about classic mistakes and exam traps.

3. **Scaffolded Practice Arena**:
   - Generates 3 tiered practice challenges:
     - *Tier 1: Quick Concept Check (Multiple Choice / True-False)*
     - *Tier 2: Application Problem (Numerical / Code / Conceptual Reasoning)*
     - *Tier 3: Mastery Challenge (Deep Transfer & Boundary Conditions)*
   - Multi-stage progressive hints (*Nudge $\to$ Clue $\to$ Solution Walkthrough*).

4. **Rubric-Based AI Answer Evaluation & Constructive Feedback**:
   - Scores responses on a 0–100 scale and assigns a cognitive mastery tier (*Novice $\to$ Developing $\to$ Proficient $\to$ Mastered*).
   - Generates supportive, constructive feedback highlighting what was done correctly, precisely where thinking diverged, and provides a memorable golden takeaway.

5. **Continuous Student Progress & Learning Gaps Radar**:
   - Tracks rolling concept mastery scores per subject and topic.
   - Visualizes identified learning gaps (*Open $\to$ Practicing $\to$ Resolved*).
   - Dynamic SVG progress rings, subject performance distributions, and streak counters.

6. **Hybrid AI Engine**:
   - **Live Google Gemini Integration**: Supports `gemini-1.5-flash` and `gemini-2.0-flash` when an API key is provided.
   - **Built-in Smart Pedagogical Knowledge Engine**: Operates reliably offline or without an API key, synthesizing high-quality diagnostic and practice responses for any subject.

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10+
- Dependencies installed: `Flask`, `google-generativeai`, `requests`, `python-dotenv`

### 2. Run Locally
```bash
python app.py
```
Open your browser and navigate to:
```
http://localhost:5000
```

### 3. (Optional) Configure Gemini API Key
You can add your Google Gemini API key either:
- In `.env`:
  ```env
  GEMINI_API_KEY=your_actual_key_here
  ```
- Or directly in the web UI by clicking the **Settings (⚙️)** button in the top right header.

---

## 📂 Project Architecture

```
├── app.py                  # Flask web server & REST API controller
├── agent_engine.py         # Cognitive AI Agent (Gemini + Local Fallback)
├── knowledge_base.py       # Curated domain models & misconception taxonomies
├── database.py             # SQLite persistence (mastery, gaps, submissions)
├── test_agent.py           # Automated unit and integration test suite
├── .env                    # Environment variables (API keys, ports)
├── templates/
│   └── index.html          # Semantic single-page application view
└── static/
    ├── css/style.css       # Obsidian dark glassmorphic design system
    └── js/app.js           # Client-side state manager and KaTeX renderer
```
