"""
app.py - Main Flask Web Application for Doubt-to-Learning Agent
Serves the learning studio, interactive practice arena, mastery analytics dashboard,
and REST APIs for live AI cognitive diagnosis and rubric evaluation.
"""

import os
from flask import Flask, render_template, request, jsonify
from database import (
    init_db,
    get_or_create_profile,
    update_profile_settings,
    save_doubt_session,
    record_practice_submission,
    get_doubt_by_id,
    get_dashboard_analytics,
    get_all_history,
    seed_sample_data,
    get_db_connection
)
from agent_engine import doubt_agent

app = Flask(__name__)
app.config["SECRET_KEY"] = "doubt-to-learning-secret-key-2026"

# Ensure DB tables exist on startup
init_db()

@app.route("/")
def index():
    profile = get_or_create_profile()
    return render_template("index.html", profile=profile, is_live=doubt_agent.is_live)

@app.route("/api/doubt/analyze", methods=["POST"])
def analyze_doubt_endpoint():
    data = request.get_json() or {}
    subject = data.get("subject", "General Science").strip()
    doubt_text = data.get("doubt_text", "").strip()
    context_attempt = data.get("context_attempt", "").strip()
    learning_level = data.get("learning_level", "Intermediate (High School)").strip()

    if not doubt_text:
        return jsonify({"success": False, "error": "Please provide your doubt or question."}), 400

    try:
        # Run cognitive diagnosis & pedagogical explanation synthesis
        analysis = doubt_agent.analyze_doubt(subject, doubt_text, context_attempt, learning_level)

        # Persist session to database
        doubt_id, saved_questions = save_doubt_session(analysis)
        analysis["id"] = doubt_id
        analysis["practice_questions"] = saved_questions

        return jsonify({
            "success": True,
            "data": analysis
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Analysis failed: {str(e)}"}), 500

@app.route("/api/practice/evaluate", methods=["POST"])
def evaluate_practice_endpoint():
    data = request.get_json() or {}
    question_id = data.get("question_id")
    doubt_id = data.get("doubt_id")
    student_answer = data.get("student_answer", "")

    if not question_id or not doubt_id:
        return jsonify({"success": False, "error": "Missing question_id or doubt_id"}), 400

    # Retrieve question data from database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM practice_questions WHERE id = ?", (question_id,))
    q_row = cursor.fetchone()
    conn.close()

    if not q_row:
        return jsonify({"success": False, "error": "Question not found"}), 404

    q_dict = dict(q_row)

    # Evaluate answer using agent engine
    eval_result = doubt_agent.evaluate_answer(q_dict, student_answer)

    # Persist submission & update student mastery
    submission_data = {
        "question_id": question_id,
        "doubt_id": doubt_id,
        "student_answer": student_answer,
        "score": eval_result.get("score", 0),
        "mastery_level": eval_result.get("mastery_level", "Developing"),
        "feedback": eval_result.get("feedback", ""),
        "corrective_tip": eval_result.get("corrective_tip", "")
    }
    record_practice_submission(submission_data)

    # Fetch updated dashboard numbers
    analytics = get_dashboard_analytics()

    return jsonify({
        "success": True,
        "evaluation": eval_result,
        "analytics": {
            "overall_mastery": analytics["overall_mastery"],
            "profile": analytics["profile"]
        }
    })

@app.route("/api/student/dashboard", methods=["GET"])
def dashboard_endpoint():
    analytics = get_dashboard_analytics()
    return jsonify({
        "success": True,
        "data": analytics,
        "ai_status": {
            "is_live": doubt_agent.is_live,
            "has_key": bool(doubt_agent.api_key)
        }
    })

@app.route("/api/doubts/history", methods=["GET"])
def history_endpoint():
    history = get_all_history(limit=50)
    return jsonify({
        "success": True,
        "data": history
    })

@app.route("/api/doubt/<int:doubt_id>", methods=["GET"])
def get_doubt_detail_endpoint(doubt_id):
    doubt = get_doubt_by_id(doubt_id)
    if not doubt:
        return jsonify({"success": False, "error": "Doubt not found"}), 404
    return jsonify({
        "success": True,
        "data": doubt
    })

@app.route("/api/settings/config", methods=["POST"])
def settings_config_endpoint():
    data = request.get_json() or {}
    api_key = data.get("api_key", "").strip()
    student_name = data.get("student_name", "").strip()
    learning_level = data.get("learning_level", "").strip()

    if api_key:
        doubt_agent.set_api_key(api_key)

    if student_name or learning_level:
        update_profile_settings(name=student_name or None, learning_level=learning_level or None)

    return jsonify({
        "success": True,
        "is_live": doubt_agent.is_live,
        "message": "Settings updated successfully."
    })

@app.route("/api/settings/test-key", methods=["POST"])
def test_key_endpoint():
    data = request.get_json() or {}
    api_key = data.get("api_key", "").strip()
    success, msg = doubt_agent.test_connection(api_key)
    return jsonify({
        "success": success,
        "message": msg
    })

@app.route("/api/settings/status", methods=["GET"])
def settings_status_endpoint():
    return jsonify({
        "is_live": doubt_agent.is_live,
        "has_key": bool(doubt_agent.api_key)
    })

@app.route("/api/seed-demo", methods=["POST"])
def seed_demo_endpoint():
    seed_sample_data()
    analytics = get_dashboard_analytics()
    return jsonify({
        "success": True,
        "message": "Demo sample student data initialized successfully!",
        "data": analytics
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("==================================================")
    print("Doubt-to-Learning Agent Server Starting")
    print(f"Local URL: http://localhost:{port}")
    print(f"AI Engine Mode: {'Google Gemini LIVE' if doubt_agent.is_live else 'Local Pedagogical Engine'}")
    print("==================================================")
    app.run(host="0.0.0.0", port=port, debug=False)
