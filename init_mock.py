import json
import random

questions = []
subjects = {
    "Physics": {"Easy": 15, "Medium": 20, "Hard": 10},
    "Chemistry": {"Easy": 15, "Medium": 20, "Hard": 10},
    "Biology": {"Easy": 30, "Medium": 40, "Hard": 20}
}
q_num = 1

for subj, difficulty_map in subjects.items():
    for diff, count in difficulty_map.items():
        for i in range(count):
            q_text = f"[{subj}] What is the concept behind phenomenon #{i+1}?"
            options = ["A) Option A", "B) Option B", "C) Option C", "D) Option D"]
            ans = random.choice(options)
            
            questions.append({
                "text": q_text,
                "metadata": {
                    "subject": subj,
                    "difficulty": diff,
                    "options": options,
                    "correct_answer": ans,
                    "marks": 4
                }
            })
            q_num += 1

with open('zeea_mock_db.json', 'w') as f:
    json.dump(questions, f, indent=4)
