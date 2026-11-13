"""問題の読み込み・出題・採点のロジック（画面には依存しない）。"""

import json
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path


def load_questions(data_path):
    """all.json を読み込み、問題IDをキーにした辞書を返す。"""
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"問題データが見つかりません: {path}")
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    questions = data["questions"] if isinstance(data, dict) else data
    return {question["id"]: question for question in questions}


@dataclass
class ExamItem:
    """試験中の1問。choice_order は表示順→元の選択肢添字の対応。"""

    question_id: str
    choice_order: list
    selected: list = None  # 回答した元の選択肢添字（未回答は None）
    is_correct: bool = None


@dataclass
class Exam:
    """1回分の試験の状態。"""

    exam_id: str
    items: list
    feedback: str = None  # AIによる総評（生成後に保存）
    extra: dict = field(default_factory=dict)

    @property
    def answered_count(self):
        """回答済みの問題数を返す。"""
        return sum(1 for item in self.items if item.selected is not None)

    @property
    def correct_count(self):
        """正解数を返す。"""
        return sum(1 for item in self.items if item.is_correct)

    @property
    def is_finished(self):
        """全問回答済みかを返す。"""
        return self.answered_count == len(self.items)

    @property
    def current_index(self):
        """次に回答すべき問題の添字を返す（全問回答済みなら None）。"""
        for index, item in enumerate(self.items):
            if item.selected is None:
                return index
        return None


def create_exam(questions, count, rng=None):
    """全章からランダムに count 問を選び、選択肢の順序もシャッフルした試験を作る。"""
    rng = rng or random.Random()
    question_ids = list(questions.keys())
    picked_ids = rng.sample(question_ids, min(count, len(question_ids)))
    items = []
    for question_id in picked_ids:
        choice_order = list(range(len(questions[question_id]["choices"])))
        rng.shuffle(choice_order)
        items.append(ExamItem(question_id=question_id, choice_order=choice_order))
    return Exam(exam_id=uuid.uuid4().hex, items=items)


def grade_answer(question, selected_original):
    """選択した元の選択肢添字の集合が正解と完全一致すれば正解とする。"""
    return set(selected_original) == set(question["answer"])


def submit_answer(exam, questions, index, selected_display):
    """表示順の選択肢添字で回答を受け付けて採点する。

    再回答は受け付けない。不正な回答は ValueError を送出する。
    """
    if exam.current_index != index:
        raise ValueError("この問題には回答できません（回答済み、または順番が違います）")
    item = exam.items[index]
    question = questions[item.question_id]
    if not selected_display:
        raise ValueError("選択肢を選んでください")
    if any(choice < 0 or choice >= len(item.choice_order) for choice in selected_display):
        raise ValueError("不正な選択肢です")
    if question["type"] == "single" and len(selected_display) != 1:
        raise ValueError("選択肢を1つ選んでください")
    selected_original = sorted({item.choice_order[choice] for choice in selected_display})
    item.selected = selected_original
    item.is_correct = grade_answer(question, selected_original)
    return item.is_correct


def display_choices(question, item):
    """表示順に並べた選択肢の一覧を返す（各要素は元の添字と本文）。"""
    return [
        {"display_index": display_index, "original_index": original_index,
         "text": question["choices"][original_index]}
        for display_index, original_index in enumerate(item.choice_order)
    ]


class ExamStore:
    """試験の状態をメモリ上に保持する（ローカル単一利用者向け）。"""

    def __init__(self):
        self._exams = {}

    def add(self, exam):
        """試験を登録する。"""
        self._exams[exam.exam_id] = exam

    def get(self, exam_id):
        """試験IDから試験を返す（無ければ None）。"""
        return self._exams.get(exam_id) if exam_id else None
