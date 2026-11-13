"""history.py のテスト。一時フォルダとダミーデータのみを使う。"""

import random
import tempfile
import unittest

import history
import quiz
from tests.test_quiz import make_dummy_questions


class HistoryTest(unittest.TestCase):
    """履歴の保存・更新・一覧のテスト。"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        questions = make_dummy_questions()
        self.exam = quiz.create_exam(questions, 60, random.Random(3))
        for index in range(60):
            quiz.submit_answer(self.exam, questions, index, [0])
        self.summary = quiz.summarize(self.exam, questions)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_then_add_feedback(self):
        """スコア保存後に総評を追記でき、一覧に1件だけ現れること。"""
        history.save_record(self.temp_dir.name, self.exam, self.summary)
        history.save_record(self.temp_dir.name, self.exam, self.summary, "総評テキスト", "dummy-model")
        records = history.list_records(self.temp_dir.name)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["correct"], self.exam.correct_count)
        self.assertEqual(records[0]["feedback"], "総評テキスト")

    def test_rejects_invalid_id(self):
        """パス操作につながる不正なIDを拒否すること。"""
        with self.assertRaises(ValueError):
            history.load_record(self.temp_dir.name, "../secret")


if __name__ == "__main__":
    unittest.main()
