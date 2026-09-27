import importlib.util
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
feedback_path = repo_root / 'feedback.py'

spec = importlib.util.spec_from_file_location('feedback_mod', str(feedback_path))
if spec is None or spec.loader is None:
    raise FileNotFoundError(f"Cannot load module spec or loader for {feedback_path}")
feedback_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feedback_mod)

sample = {
    'Q1': {
        'max_marks': 2,
        'marks_awarded': 1,
        'status': 'ATTEMPTED',
        'q_type': 'theory',
        'part_details': [{'marks': 2, 'awarded': 1}]
    },
    'total': {'awarded': 1, 'max': 2}
}

print(feedback_mod.generate_feedback(sample))
