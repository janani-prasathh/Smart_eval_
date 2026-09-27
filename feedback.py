def generate_feedback(evaluation_result):
    """
    Generate personalized feedback text
    
    Args:
        evaluation_result: Dict with evaluation data
        
    Returns:
        str: Formatted feedback text
    """
    feedback_lines = []
    feedback_lines.append("=" * 70)
    feedback_lines.append("PERSONALIZED FEEDBACK REPORT")
    feedback_lines.append("=" * 70)
    feedback_lines.append("")
    
    # Overall score
    total = evaluation_result.get('total', {})
    total_awarded = total.get('awarded', 0)
    total_max = total.get('max', 0)
    percentage = (total_awarded / total_max * 100) if total_max > 0 else 0
    
    feedback_lines.append(f"Overall Score: {total_awarded:.1f} / {total_max:.1f} ({percentage:.1f}%)")
    feedback_lines.append("")
    
    # Performance level
    if percentage >= 90:
        feedback_lines.append("🌟 OUTSTANDING PERFORMANCE!")
        feedback_lines.append("You have demonstrated exceptional mastery of the subject.")
    elif percentage >= 80:
        feedback_lines.append("⭐ EXCELLENT PERFORMANCE!")
        feedback_lines.append("You have shown strong understanding of key concepts.")
    elif percentage >= 70:
        feedback_lines.append("✓ VERY GOOD PERFORMANCE!")
        feedback_lines.append("You have a solid grasp of most topics.")
    elif percentage >= 60:
        feedback_lines.append("✓ GOOD PERFORMANCE!")
        feedback_lines.append("You have demonstrated satisfactory knowledge.")
    elif percentage >= 50:
        feedback_lines.append("⚠ SATISFACTORY PERFORMANCE")
        feedback_lines.append("There is room for improvement in several areas.")
    else:
        feedback_lines.append("⚠ NEEDS IMPROVEMENT")
        feedback_lines.append("Please focus on strengthening fundamental concepts.")
    
    feedback_lines.append("")
    feedback_lines.append("=" * 70)
    feedback_lines.append("QUESTION-WISE BREAKDOWN")
    feedback_lines.append("=" * 70)
    feedback_lines.append("")
    
    # Question-wise feedback
    for key, value in evaluation_result.items():
        if key == 'total':
            continue
        
        if isinstance(value, dict) and 'marks_awarded' in value:
            q_max = value.get('max_marks', 0)
            q_awarded = value.get('marks_awarded', 0)
            q_percentage = (q_awarded / q_max * 100) if q_max > 0 else 0
            status = value.get('status', 'ATTEMPTED')
            
            feedback_lines.append(f"{key}:")
            feedback_lines.append(f"  Score: {q_awarded:.1f} / {q_max:.1f} ({q_percentage:.1f}%)")
            feedback_lines.append(f"  Status: {status}")
            
            if q_percentage >= 80:
                feedback_lines.append("  ✓ Excellent work on this question!")
            elif q_percentage >= 60:
                feedback_lines.append("  ✓ Good attempt, minor improvements needed.")
            elif q_percentage >= 40:
                feedback_lines.append("  ⚠ Fair attempt, review key concepts.")
            else:
                feedback_lines.append("  ⚠ Needs significant improvement.")
            
            feedback_lines.append("")
    
    feedback_lines.append("=" * 70)
    feedback_lines.append("RECOMMENDATIONS")
    feedback_lines.append("=" * 70)
    feedback_lines.append("")
    
    # Recommendations based on performance
    if percentage < 60:
        feedback_lines.append("• Review lecture notes and textbook materials thoroughly")
        feedback_lines.append("• Practice more problems from each topic")
        feedback_lines.append("• Attend office hours or tutoring sessions")
        feedback_lines.append("• Form study groups with classmates")
    
    if percentage >= 60 and percentage < 80:
        feedback_lines.append("• Focus on topics where you scored below 70%")
        feedback_lines.append("• Practice writing complete, detailed answers")
        feedback_lines.append("• Include diagrams when specified")
        feedback_lines.append("• Review and strengthen weak areas")
    
    if percentage >= 80:
        feedback_lines.append("• Maintain your excellent study habits")
        feedback_lines.append("• Challenge yourself with advanced problems")
        feedback_lines.append("• Help peers who are struggling")
        feedback_lines.append("• Continue to include detailed explanations")
    
    feedback_lines.append("")
    feedback_lines.append("=" * 70)
    feedback_lines.append("END OF FEEDBACK")
    feedback_lines.append("=" * 70)
    
    return "\n".join(feedback_lines)
