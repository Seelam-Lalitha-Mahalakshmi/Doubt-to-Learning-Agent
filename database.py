"""
database.py - Persistent Storage for Doubt-to-Learning Agent
Handles student profiles, doubt sessions, practice questions, rubric submissions,
concept mastery scores, and detected learning gaps using SQLite.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "doubt_learning.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Student Profile
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT DEFAULT 'Learner',
        learning_level TEXT DEFAULT 'Intermediate (High School)',
        total_doubts INTEGER DEFAULT 0,
        questions_attempted INTEGER DEFAULT 0,
        questions_correct INTEGER DEFAULT 0,
        streak_days INTEGER DEFAULT 1,
        last_active_date TEXT,
        created_at TEXT
    )
    """)

    # 2. Doubt Sessions & Explanations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS doubts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_uuid TEXT UNIQUE,
        subject TEXT NOT NULL,
        doubt_text TEXT NOT NULL,
        context_attempt TEXT,
        learning_level TEXT NOT NULL,
        diagnosed_concept TEXT NOT NULL,
        misconception_gap TEXT NOT NULL,
        prerequisites TEXT, -- JSON list
        mental_model_analogy TEXT,
        explanation_steps TEXT, -- JSON list of steps
        common_pitfalls TEXT, -- JSON list
        created_at TEXT
    )
    """)

    # 3. Practice Questions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS practice_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doubt_id INTEGER NOT NULL,
        question_tier INTEGER DEFAULT 1, -- 1: Concept Check, 2: Application, 3: Mastery
        question_text TEXT NOT NULL,
        question_type TEXT NOT NULL, -- 'mcq' or 'open'
        options TEXT, -- JSON list for MCQ
        correct_answer TEXT NOT NULL,
        explanation TEXT NOT NULL,
        hints TEXT, -- JSON list
        FOREIGN KEY (doubt_id) REFERENCES doubts(id) ON DELETE CASCADE
    )
    """)

    # 4. Practice Submissions & AI Feedback
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS practice_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        doubt_id INTEGER NOT NULL,
        student_answer TEXT NOT NULL,
        score INTEGER NOT NULL, -- 0 to 100
        is_correct INTEGER NOT NULL, -- 0 or 1
        mastery_level TEXT NOT NULL, -- Novice, Developing, Proficient, Mastered
        feedback TEXT NOT NULL,
        corrective_tip TEXT,
        created_at TEXT,
        FOREIGN KEY (question_id) REFERENCES practice_questions(id) ON DELETE CASCADE,
        FOREIGN KEY (doubt_id) REFERENCES doubts(id) ON DELETE CASCADE
    )
    """)

    # 5. Concept Mastery Matrix
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS concept_mastery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        concept_name TEXT NOT NULL,
        mastery_score INTEGER DEFAULT 0, -- 0 to 100
        attempts_count INTEGER DEFAULT 0,
        correct_count INTEGER DEFAULT 0,
        last_practiced TEXT,
        UNIQUE(subject, concept_name)
    )
    """)

    # 6. Learning Gaps Tracker
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS learning_gaps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        concept_name TEXT NOT NULL,
        gap_description TEXT NOT NULL,
        status TEXT DEFAULT 'open', -- 'open', 'practicing', 'resolved'
        identified_at TEXT,
        resolved_at TEXT
    )
    """)

    conn.commit()

    # Ensure a default profile exists
    cursor.execute("SELECT COUNT(*) FROM student_profile")
    if cursor.fetchone()[0] == 0:
        now = datetime.utcnow().isoformat()
        cursor.execute("""
        INSERT INTO student_profile (name, learning_level, total_doubts, questions_attempted, questions_correct, streak_days, last_active_date, created_at)
        VALUES ('Alex Rivera', 'Intermediate (High School)', 0, 0, 0, 3, ?, ?)
        """, (now, now))
        conn.commit()

    conn.close()

def get_or_create_profile():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_profile ORDER BY id ASC LIMIT 1")
    profile = cursor.fetchone()
    if not profile:
        now = datetime.utcnow().isoformat()
        cursor.execute("""
        INSERT INTO student_profile (name, learning_level, total_doubts, questions_attempted, questions_correct, streak_days, last_active_date, created_at)
        VALUES ('Alex Rivera', 'Intermediate (High School)', 0, 0, 0, 3, ?, ?)
        """, (now, now))
        conn.commit()
        cursor.execute("SELECT * FROM student_profile ORDER BY id ASC LIMIT 1")
        profile = cursor.fetchone()
    conn.close()
    return dict(profile)

def update_profile_settings(name=None, learning_level=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if name:
        cursor.execute("UPDATE student_profile SET name = ? WHERE id = 1", (name,))
    if learning_level:
        cursor.execute("UPDATE student_profile SET learning_level = ? WHERE id = 1", (learning_level,))
    conn.commit()
    conn.close()

def save_doubt_session(session_data):
    """
    Saves a full doubt analysis session along with generated practice questions.
    Returns the doubt_id and list of created practice questions.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute("""
    INSERT INTO doubts (
        session_uuid, subject, doubt_text, context_attempt, learning_level,
        diagnosed_concept, misconception_gap, prerequisites, mental_model_analogy,
        explanation_steps, common_pitfalls, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_data.get("session_uuid"),
        session_data.get("subject"),
        session_data.get("doubt_text"),
        session_data.get("context_attempt", ""),
        session_data.get("learning_level"),
        session_data.get("diagnosed_concept"),
        session_data.get("misconception_gap"),
        json.dumps(session_data.get("prerequisites", [])),
        session_data.get("mental_model_analogy", ""),
        json.dumps(session_data.get("explanation_steps", [])),
        json.dumps(session_data.get("common_pitfalls", [])),
        now
    ))
    doubt_id = cursor.lastrowid

    # Increment profile total doubts count
    cursor.execute("UPDATE student_profile SET total_doubts = total_doubts + 1, last_active_date = ? WHERE id = 1", (now,))

    # Insert learning gap if not already present
    cursor.execute("""
    SELECT id FROM learning_gaps
    WHERE subject = ? AND concept_name = ? AND status = 'open'
    """, (session_data.get("subject"), session_data.get("diagnosed_concept")))
    existing_gap = cursor.fetchone()
    if not existing_gap:
        cursor.execute("""
        INSERT INTO learning_gaps (subject, concept_name, gap_description, status, identified_at)
        VALUES (?, ?, ?, 'open', ?)
        """, (
            session_data.get("subject"),
            session_data.get("diagnosed_concept"),
            session_data.get("misconception_gap"),
            now
        ))

    # Ensure concept exists in concept_mastery table
    cursor.execute("""
    SELECT id, mastery_score FROM concept_mastery
    WHERE subject = ? AND concept_name = ?
    """, (session_data.get("subject"), session_data.get("diagnosed_concept")))
    row = cursor.fetchone()
    if not row:
        cursor.execute("""
        INSERT INTO concept_mastery (subject, concept_name, mastery_score, attempts_count, correct_count, last_practiced)
        VALUES (?, ?, 35, 0, 0, ?)
        """, (session_data.get("subject"), session_data.get("diagnosed_concept"), now))

    # Insert practice questions
    saved_questions = []
    questions_list = session_data.get("practice_questions", [])
    for idx, q in enumerate(questions_list):
        tier = q.get("question_tier", idx + 1)
        q_text = q.get("question_text", "")
        q_type = q.get("question_type", "mcq")
        opts = json.dumps(q.get("options", [])) if q.get("options") else None
        ans = q.get("correct_answer", "")
        exp = q.get("explanation", "")
        hints = json.dumps(q.get("hints", []))

        cursor.execute("""
        INSERT INTO practice_questions (doubt_id, question_tier, question_text, question_type, options, correct_answer, explanation, hints)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (doubt_id, tier, q_text, q_type, opts, ans, exp, hints))
        saved_q_id = cursor.lastrowid
        saved_questions.append({
            "id": saved_q_id,
            "question_tier": tier,
            "question_text": q_text,
            "question_type": q_type,
            "options": q.get("options", []),
            "hints": q.get("hints", []),
            "correct_answer": ans,
            "explanation": exp
        })

    conn.commit()
    conn.close()

    return doubt_id, saved_questions

def record_practice_submission(submission_data):
    """
    Records a student's answer submission, updates mastery scores and gap status.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    question_id = submission_data["question_id"]
    doubt_id = submission_data["doubt_id"]
    student_answer = submission_data["student_answer"]
    score = int(submission_data["score"])
    is_correct = 1 if score >= 70 else 0
    mastery_level = submission_data.get("mastery_level", "Developing")
    feedback = submission_data.get("feedback", "")
    corrective_tip = submission_data.get("corrective_tip", "")

    # Save submission
    cursor.execute("""
    INSERT INTO practice_submissions (
        question_id, doubt_id, student_answer, score, is_correct, mastery_level, feedback, corrective_tip, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        question_id, doubt_id, student_answer, score, is_correct, mastery_level, feedback, corrective_tip, now
    ))

    # Update student profile stats
    cursor.execute("""
    UPDATE student_profile
    SET questions_attempted = questions_attempted + 1,
        questions_correct = questions_correct + ?,
        last_active_date = ?
    WHERE id = 1
    """, (is_correct, now))

    # Find doubt details to update concept mastery
    cursor.execute("SELECT subject, diagnosed_concept FROM doubts WHERE id = ?", (doubt_id,))
    d_row = cursor.fetchone()
    if d_row:
        subject = d_row["subject"]
        concept = d_row["diagnosed_concept"]

        cursor.execute("SELECT mastery_score, attempts_count, correct_count FROM concept_mastery WHERE subject = ? AND concept_name = ?", (subject, concept))
        c_row = cursor.fetchone()

        if c_row:
            old_score = c_row["mastery_score"]
            new_attempts = c_row["attempts_count"] + 1
            new_correct = c_row["correct_count"] + is_correct
            # Adaptive calculation: Weighted rolling update towards new score
            calculated_mastery = int(old_score * 0.6 + score * 0.4)
            calculated_mastery = max(10, min(100, calculated_mastery))

            cursor.execute("""
            UPDATE concept_mastery
            SET mastery_score = ?, attempts_count = ?, correct_count = ?, last_practiced = ?
            WHERE subject = ? AND concept_name = ?
            """, (calculated_mastery, new_attempts, new_correct, now, subject, concept))

            # If mastery reaches >= 80, resolve learning gap
            if calculated_mastery >= 80:
                cursor.execute("""
                UPDATE learning_gaps
                SET status = 'resolved', resolved_at = ?
                WHERE subject = ? AND concept_name = ? AND status != 'resolved'
                """, (now, subject, concept))
            else:
                cursor.execute("""
                UPDATE learning_gaps
                SET status = 'practicing'
                WHERE subject = ? AND concept_name = ? AND status = 'open'
                """, (subject, concept))

    conn.commit()
    conn.close()

def get_doubt_by_id(doubt_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doubts WHERE id = ?", (doubt_id,))
    doubt = cursor.fetchone()
    if not doubt:
        conn.close()
        return None

    doubt_dict = dict(doubt)
    doubt_dict["prerequisites"] = json.loads(doubt_dict["prerequisites"] or "[]")
    doubt_dict["explanation_steps"] = json.loads(doubt_dict["explanation_steps"] or "[]")
    doubt_dict["common_pitfalls"] = json.loads(doubt_dict["common_pitfalls"] or "[]")

    # Get questions
    cursor.execute("SELECT * FROM practice_questions WHERE doubt_id = ? ORDER BY question_tier ASC", (doubt_id,))
    questions = []
    for q in cursor.fetchall():
        q_dict = dict(q)
        q_dict["options"] = json.loads(q_dict["options"]) if q_dict["options"] else []
        q_dict["hints"] = json.loads(q_dict["hints"] or "[]")

        # Check if student already submitted an answer for this question
        cursor.execute("SELECT * FROM practice_submissions WHERE question_id = ? ORDER BY id DESC LIMIT 1", (q["id"],))
        sub = cursor.fetchone()
        q_dict["submission"] = dict(sub) if sub else None

        questions.append(q_dict)

    doubt_dict["questions"] = questions
    conn.close()
    return doubt_dict

def get_dashboard_analytics():
    conn = get_db_connection()
    cursor = conn.cursor()

    profile = get_or_create_profile()

    # Concept masteries grouped by subject
    cursor.execute("SELECT * FROM concept_mastery ORDER BY mastery_score DESC")
    masteries = [dict(row) for row in cursor.fetchall()]

    # Learning gaps
    cursor.execute("SELECT * FROM learning_gaps ORDER BY CASE WHEN status = 'open' THEN 1 WHEN status = 'practicing' THEN 2 ELSE 3 END, id DESC")
    gaps = [dict(row) for row in cursor.fetchall()]

    # Subject aggregates
    cursor.execute("""
    SELECT subject,
           ROUND(AVG(mastery_score), 1) as avg_mastery,
           COUNT(*) as concept_count
    FROM concept_mastery
    GROUP BY subject
    """)
    subject_stats = [dict(row) for row in cursor.fetchall()]

    # Global Mastery Percentage
    cursor.execute("SELECT ROUND(AVG(mastery_score), 1) as overall_mastery FROM concept_mastery")
    overall_row = cursor.fetchone()
    overall_mastery = overall_row["overall_mastery"] if overall_row and overall_row["overall_mastery"] is not None else 0

    # Recent resolved doubts
    cursor.execute("SELECT id, session_uuid, subject, doubt_text, diagnosed_concept, misconception_gap, created_at FROM doubts ORDER BY id DESC LIMIT 6")
    recent_doubts = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "profile": profile,
        "overall_mastery": overall_mastery,
        "subject_stats": subject_stats,
        "masteries": masteries,
        "gaps": gaps,
        "recent_doubts": recent_doubts
    }

def get_all_history(limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT d.id, d.subject, d.doubt_text, d.diagnosed_concept, d.misconception_gap, d.learning_level, d.created_at,
           COUNT(DISTINCT pq.id) as question_count,
           COUNT(DISTINCT ps.id) as answers_submitted
    FROM doubts d
    LEFT JOIN practice_questions pq ON d.id = pq.doubt_id
    LEFT JOIN practice_submissions ps ON d.id = ps.doubt_id
    GROUP BY d.id
    ORDER BY d.id DESC
    LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def seed_sample_data():
    """Seeds initial demonstration data showcasing multi-subject mastery and learning gaps."""
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    # Reset tables cleanly
    cursor.execute("DELETE FROM practice_submissions")
    cursor.execute("DELETE FROM practice_questions")
    cursor.execute("DELETE FROM doubts")
    cursor.execute("DELETE FROM concept_mastery")
    cursor.execute("DELETE FROM learning_gaps")

    cursor.execute("""
    UPDATE student_profile
    SET total_doubts = 4, questions_attempted = 7, questions_correct = 5, streak_days = 4, last_active_date = ?
    WHERE id = 1
    """, (now,))

    # Seed Concept Masteries
    concepts = [
        ("Physics", "Newton's Third Law vs Normal Force", 88, 5, 4),
        ("Physics", "Conservation of Angular Momentum", 55, 2, 1),
        ("Mathematics", "Calculus: Chain Rule & Function Composition", 92, 6, 6),
        ("Mathematics", "Inequalities & Sign Inversion", 75, 4, 3),
        ("Chemistry", "Le Chatelier's Principle & Dynamic Equilibrium", 82, 4, 3),
        ("Computer Science", "Recursion & Base Cases vs Stack Overflow", 68, 3, 2),
        ("Biology", "Cellular Respiration vs Photosynthesis", 90, 5, 5),
    ]
    for subj, conc, mast, att, corr in concepts:
        cursor.execute("""
        INSERT INTO concept_mastery (subject, concept_name, mastery_score, attempts_count, correct_count, last_practiced)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (subj, conc, mast, att, corr, now))

    # Seed Learning Gaps
    gaps = [
        ("Physics", "Conservation of Angular Momentum", "Treating moment of inertia as a constant scalar regardless of mass distribution changes.", "open"),
        ("Computer Science", "Recursion & Base Cases vs Stack Overflow", "Forgetting to reduce problem size towards base case in the recursive leap.", "practicing"),
        ("Physics", "Newton's Third Law vs Normal Force", "Conflating action-reaction pair with balanced forces acting on a single body.", "resolved"),
        ("Mathematics", "Inequalities & Sign Inversion", "Applying standard equation balancing rules without flipping sign during negative multiplication.", "resolved"),
    ]
    for subj, conc, gap_desc, status in gaps:
        res_date = now if status == 'resolved' else None
        cursor.execute("""
        INSERT INTO learning_gaps (subject, concept_name, gap_description, status, identified_at, resolved_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (subj, conc, gap_desc, status, now, res_date))

    conn.commit()
    conn.close()

# Initialize DB on module import
init_db()
