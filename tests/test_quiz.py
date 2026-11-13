"""quiz.py のテスト。本物の問題文は使わず、ダミーデータのみを使う。"""

import random
import unittest

import quiz


def make_dummy_questions(count=70):
    """ダミーの問題データを生成する。"""
    questions = {}
    for number in range(count):
        is_multiple = number % 4 == 0
        questions[f"dummy-{number:03d}"] = {
            "id": f"dummy-{number:03d}",
            "chapter": number % 5 + 1,
            "section": "ダミー中項目",
            "syllabusRef": f"{number % 5 + 1}-1",
            "type": "multiple" if is_multiple else "single",
            "question": f"ダミー問題{number}",
            "choices": ["選択肢甲", "選択肢乙", "選択肢丙", "選択肢丁"],
            "answer": [0, 2] if is_multiple else [number % 4],
            "explanation": "ダミー解説",
            "volatile": False,
        }
    return questions


class QuizTest(unittest.TestCase):
    """出題と採点のテスト。"""

    def setUp(self):
        self.questions = make_dummy_questions()
        self.exam = quiz.create_exam(self.questions, 60, random.Random(1))

    def test_create_exam_picks_unique_questions(self):
        """60問が重複なく選ばれ、選択肢の順序が並べ替えであること。"""
        ids = [item.question_id for item in self.exam.items]
        self.assertEqual(len(ids), 60)
        self.assertEqual(len(set(ids)), 60)
        for item in self.exam.items:
            self.assertEqual(sorted(item.choice_order), [0, 1, 2, 3])

    def test_correct_answer_by_content(self):
        """シャッフル後も、内容に紐づけて正解判定できること。"""
        item = self.exam.items[0]
        question = self.questions[item.question_id]
        selected = [item.choice_order.index(original) for original in question["answer"]]
        self.assertTrue(quiz.submit_answer(self.exam, self.questions, 0, selected))
        self.assertEqual(self.exam.correct_count, 1)

    def test_cannot_answer_twice_or_skip(self):
        """回答済みの問題への再回答と、先の問題への回答を拒否すること。"""
        quiz.submit_answer(self.exam, self.questions, 0, [0])
        with self.assertRaises(ValueError):
            quiz.submit_answer(self.exam, self.questions, 0, [1])
        with self.assertRaises(ValueError):
            quiz.submit_answer(self.exam, self.questions, 5, [1])

    def test_multiple_requires_exact_match(self):
        """複数選択は過不足なく選んだ場合のみ正解とすること。"""
        question = {"type": "multiple", "answer": [0, 2]}
        self.assertTrue(quiz.grade_answer(question, [2, 0]))
        self.assertFalse(quiz.grade_answer(question, [0]))
        self.assertFalse(quiz.grade_answer(question, [0, 1, 2]))

    def test_finish_after_all_answers(self):
        """全問回答で終了状態になること。"""
        for index in range(60):
            quiz.submit_answer(self.exam, self.questions, index, [0])
        self.assertTrue(self.exam.is_finished)
        self.assertIsNone(self.exam.current_index)


if __name__ == "__main__":
    unittest.main()
