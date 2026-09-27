"""
evaluation_mode.py

Applies evaluation modes (Lenient, Strict, Moderate) to a score.
"""

def apply_evaluation_mode(original_score: float, max_marks: float, mode: str) -> tuple[float, float, str]:
    """
    Adjusts a score based on the selected evaluation mode.

    Args:
        original_score (float): The score from the AI.
        max_marks (float): The maximum possible marks.
        mode (str): "Lenient", "Strict", or "Moderate".

    Returns:
        tuple: (adjusted_score, original_score, mode)
    """
    if max_marks == 0:
        return original_score, original_score, mode

    percentage = (original_score / max_marks) * 100
    adjusted_score = original_score
    
    if mode == "Lenient":
        if percentage < 35.0:
            adjusted_score = min(original_score + 5.0, max_marks)
    elif mode == "Strict":
        if percentage > 80.0:
            adjusted_score = max(original_score - 5.0, 0.0)
    
    # "Moderate" mode does nothing, so adjusted_score remains original_score

    return round(adjusted_score, 1), round(original_score, 1), mode