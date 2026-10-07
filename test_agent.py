"""
test_agent.py - Comprehensive Unit & Integration Tests for Doubt-to-Learning Agent
Verifies cognitive diagnosis, explanation generation, answer grading, database persistence, and mastery tracking.
"""

import sys
import os
from database import (
    init_db,
    save_doubt_session,
    record_practice_submission,
    get_doubt_by_id,
    get_dashboard_analytics,
    seed_sample_data,
    get_or_create_profile
)
from agent_engine import doubt_agent

def run_tests():
    print("==================================================")
    print("[TEST] Running Doubt-to-Learning Agent Test Suite")
    print("==================================================")

    # 1. Test Database Initialization & Profile
    print("[1/5] Testing database init and profile...")
    init_db()
    profile = get_or_create_profile()
    assert profile is not None, "Profile should exist"
    assert "name" in profile, "Profile must have a name"
    print("  [PASS] Database initialized successfully.")

    # 2. Test Cognitive Diagnosis across multiple subjects
    print("[2/5] Testing cognitive diagnosis & pedagogical reasoning...")
    test_doubts = [
        ("Physics", "Why does an object keep moving if no force is applied to it?", "Newton's First Law"),
        ("Mathematics", "Why do we flip the inequality sign when dividing by a negative number?", "Inequalities"),
        ("Computer Science", "Why do I get a stack overflow error in my recursive function?", "Recursion")
    ]

    for subject, query, expected_keyword in test_doubts:
        res = doubt_agent.analyze_doubt(subject, query, "", "Intermediate (High School)")
        assert res.get("diagnosed_concept"), f"Should diagnose concept for {subject}"
        assert res.get("misconception_gap"), f"Should detect learning gap for {subject}"
        assert len(res.get("explanation_steps", [])) >= 2, f"Should have step-by-step breakdown for {subject}"
        assert len(res.get("practice_questions", [])) >= 2, f"Should have practice questions for {subject}"
        print(f"  [PASS] {subject}: Diagnosed '{res.get('diagnosed_concept')}' (Gap: {res.get('misconception_gap')[:50]}...)")

    # 3. Test Session Persistence
    print("[3/5] Testing session persistence in database...")
    sample_analysis = doubt_agent.analyze_doubt(
        "Physics",
        "Why don't action and reaction forces cancel each other out?",
        "I thought if F1 = -F2 then total force is zero.",
        "Intermediate (High School)"
    )
    doubt_id, saved_questions = save_doubt_session(sample_analysis)
    assert doubt_id > 0, "Doubt ID should be positive integer"
    assert len(saved_questions) >= 3, "Saved questions should have at least 3 items"

    retrieved = get_doubt_by_id(doubt_id)
    assert retrieved is not None, "Retrieved session should not be None"
    assert retrieved["subject"] == "Physics"
    print(f"  [PASS] Saved doubt session #{doubt_id} with {len(saved_questions)} practice questions.")

    # 4. Test Rubric Answer Evaluation & Mastery Tracking
    print("[4/5] Testing answer evaluation and mastery update...")
    q1 = saved_questions[0]
    eval_result = doubt_agent.evaluate_answer(q1, q1["correct_answer"])
    assert eval_result["score"] >= 80, "Correct answer should receive high score"
    assert eval_result["is_correct"] is True, "is_correct should be True for correct answer"
    print(f"  [PASS] MCQ evaluation passed: Score={eval_result['score']}, Feedback: {eval_result['feedback'][:60]}...")

    # Record submission
    record_practice_submission({
        "question_id": q1["id"],
        "doubt_id": doubt_id,
        "student_answer": q1["correct_answer"],
        "score": eval_result["score"],
        "mastery_level": eval_result["mastery_level"],
        "feedback": eval_result["feedback"],
        "corrective_tip": eval_result["corrective_tip"]
    })

    # 5. Test Analytics & Knowledge Dashboard
    print("[5/5] Testing dashboard analytics and demo seeding...")
    seed_sample_data()
    analytics = get_dashboard_analytics()
    assert analytics["overall_mastery"] > 0, "Overall mastery should be calculated"
    assert len(analytics["masteries"]) > 0, "Concept masteries list should not be empty"
    assert len(analytics["gaps"]) > 0, "Learning gaps list should not be empty"
    print(f"  [PASS] Overall Mastery: {analytics['overall_mastery']}%")
    print(f"  [PASS] Tracked concepts: {len(analytics['masteries'])}, Learning gaps: {len(analytics['gaps'])}")

    print("\n[SUCCESS] ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
