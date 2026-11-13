"""feedback.py のテスト。ダミーデータで、問題文が送信内容に含まれないことを確認する。"""

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

    def test_payload_excludes_question_text(self):
        """問題文・選択肢・解説が送信データに含まれないこと。"""
        payload = feedback.build_payload(self.exam, self.questions, self.summary)
        text = json.dumps(payload, ensure_ascii=False)
        for word in ("ダミー問題", "選択肢甲", "ダミー解説"):
            self.assertNotIn(word, text)
        self.assertEqual(len(payload["answers"]), 60)

    def test_missing_api_key(self):
        """APIキー未設定時は FeedbackError になること。"""
        with self.assertRaises(feedback.FeedbackError):
            feedback.generate_feedback("", "gemini-2.5-flash", {})


if __name__ == "__main__":
    unittest.main()
