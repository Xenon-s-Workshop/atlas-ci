import csv
import io
from typing import List, Dict

class CSVParser:
    @staticmethod
    def parse_csv_file(file_content: bytes) -> List[Dict]:
        questions = []
        try:
            content = file_content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            for row in csv_reader:
                if not row.get('questions'):
                    continue
                options = [row.get(f'option{i}', '') for i in range(1, 6) if row.get(f'option{i}')]
                if len(options) < 2:
                    continue
                try:
                    answer_num = int(row.get('answer', '1'))
                    correct_index = max(0, min(answer_num - 1, len(options) - 1))
                except:
                    correct_index = 0
                questions.append({
                    'question_description': row.get('questions', '').strip(),
                    'options': options,
                    'correct_answer_index': correct_index,
                    'correct_option': chr(65 + correct_index),
                    'explanation': row.get('explanation', '').strip()
                })
            return questions
        except Exception as e:
            raise Exception(f"CSV parse error: {e}")

class CSVGenerator:
    @staticmethod
    def questions_to_csv(questions: List[Dict], output_path):
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['questions', 'option1', 'option2', 'option3', 'option4', 'option5', 'answer', 'explanation', 'type', 'section'])
            writer.writeheader()
            for q in questions:
                opts = q.get('options', [])
                while len(opts) < 5:
                    opts.append('')
                correct_idx = q.get('correct_answer_index', -1)
                writer.writerow({
                    'questions': q.get('question_description', ''),
                    'option1': opts[0] if len(opts) > 0 else '',
                    'option2': opts[1] if len(opts) > 1 else '',
                    'option3': opts[2] if len(opts) > 2 else '',
                    'option4': opts[3] if len(opts) > 3 else '',
                    'option5': opts[4] if len(opts) > 4 else '',
                    'answer': str(correct_idx + 1) if correct_idx >= 0 else '',
                    'explanation': q.get('explanation', ''),
                    'type': '1',
                    'section': '1'
                })
