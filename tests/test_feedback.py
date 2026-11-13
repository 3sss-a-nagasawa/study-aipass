"""feedback.py のテスト。ダミーデータのみを使う。"""

import json
import random
import unittest

import feedback
import quiz
from tests.test_quiz import make_dummy_questions


class FeedbackTest(unittest.TestCase):
    """送信データとエラー処理のテスト。"""

    def setUp(self):
        self.questions = make_dummy_questions()
        self.exam = quiz.create_exam(self.questions, 60, random.Random(2))
        for index in range(60):
            quiz.submit_answer(self.exam, self.questions, index, [0])
        self.summary = quiz.summarize(self.exam, self.questions)

    def test_payload_contents(self):
        """全問の問題文を含み、誤答のみ選択肢・回答・正解を含むこと。"""
        payload = feedback.build_payload(self.exam, self.questions, self.summary)
        self.assertEqual(len(payload["answers"]), 60)
        for entry, item in zip(payload["answers"], self.exam.items):
            self.assertIn("ダミー問題", entry["question"])
            self.assertEqual("answer" in entry, not item.is_correct)
        self.assertIn("ダミー問題", feedback.build_prompt(payload))
        # 解説は送信しない（トークン節約）
        self.assertNotIn("ダミー解説", json.dumps(payload, ensure_ascii=False))

    def test_missing_api_key(self):
        """APIキー未設定時は FeedbackError になること。"""
        with self.assertRaises(feedback.FeedbackError):
            feedback.generate_feedback("", "gemini-2.5-flash", {})


if __name__ == "__main__":
    unittest.main()
