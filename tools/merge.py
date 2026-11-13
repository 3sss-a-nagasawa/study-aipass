"""全章の問題データを統合し、重複候補と形式の偏りを調べるスクリプト。

使い方:
    python merge.py

処理内容:
    1. data/chapter1〜5.json を読み込み、data/all.json に統合する
    2. 問題文が似ている組（重複候補）を一覧にする
    3. 単一選択で「正解が最長の選択肢」になっている割合を章ごとに集計する
    4. 全体の正解位置の分布を集計する
"""
import json
import os
import sys
from collections import Counter
from itertools import combinations

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
CHAPTER_FILES = [f"chapter{number}.json" for number in range(1, 6)]
SIMILARITY_THRESHOLD = 0.45


def load_questions():
    """各章のファイルを読み込み、問題のリストを返す。"""
    all_questions = []
    for file_name in CHAPTER_FILES:
        with open(os.path.join(BASE_DIR, file_name), encoding="utf-8") as file:
            all_questions.extend(json.load(file)["questions"])
    return all_questions


def bigrams(text):
    """文字2-gramの集合を返す（日本語の類似度計算用）。"""
    compact = "".join(text.split())
    return {compact[index:index + 2] for index in range(len(compact) - 1)}


def similarity(first, second):
    """2つの集合のJaccard係数を返す。"""
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def find_duplicates(questions):
    """問題文と選択肢が似ている組を、類似度の高い順に返す。"""
    grams = [bigrams(item["question"] + "".join(item["choices"][index] for index in item["answer"]))
             for item in questions]
    pairs = []
    for left, right in combinations(range(len(questions)), 2):
        score = similarity(grams[left], grams[right])
        if score >= SIMILARITY_THRESHOLD:
            pairs.append((score, questions[left]["id"], questions[right]["id"]))
    return sorted(pairs, reverse=True)


def longest_answer_ratio(questions):
    """単一選択で、正解が最長の選択肢になっている割合を章ごとに返す。"""
    result = {}
    for chapter in sorted({item["chapter"] for item in questions}):
        singles = [item for item in questions if item["chapter"] == chapter and item["type"] == "single"]
        # 正解が「単独で」最長の問題だけを数える（同じ長さで並ぶ場合は手がかりにならないため除く）
        hit = 0
        for item in singles:
            lengths = [len(choice) for choice in item["choices"]]
            answer_length = lengths[item["answer"][0]]
            if answer_length == max(lengths) and lengths.count(answer_length) == 1:
                hit += 1
        result[chapter] = (hit, len(singles))
    return result


def main():
    questions = load_questions()
    ids = Counter(item["id"] for item in questions)
    duplicated_ids = [question_id for question_id, count in ids.items() if count > 1]

    output_path = os.path.join(BASE_DIR, "all.json")
    chapter_counter = Counter(item["chapter"] for item in questions)
    merged = {
        "meta": {
            "title": "生成AIパスポート 模擬問題集（全章）",
            "createdAt": "2026-11-12",
            "syllabus": "2027年2月試験〜の新シラバス",
            "note": "オリジナル作成。answer は choices の0始まり添字の配列。volatile=true は要再確認。",
            "count": len(questions),
        },
        "questions": questions,
    }
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(merged, file, ensure_ascii=False, indent=2)

    print(f"統合: {len(questions)}問 → all.json")
    print("章別:", dict(sorted(chapter_counter.items())))
    print("ID重複:", duplicated_ids if duplicated_ids else "なし")
    print("volatile=true:", sum(1 for item in questions if item["volatile"]), "問")

    # 公式シラバスの中項目（syllabusRef）別の件数と、付け忘れの確認
    missing_ref = [item["id"] for item in questions if not item.get("syllabusRef")]
    print("syllabusRef 未設定:", missing_ref if missing_ref else "なし")
    ref_counter = Counter(item.get("syllabusRef") for item in questions)
    print("中項目別の件数:")
    for ref in sorted(key for key in ref_counter if key):
        names = {item["section"] for item in questions if item.get("syllabusRef") == ref}
        print(f"  {ref}: {ref_counter[ref]}問 {'/'.join(sorted(names))}")

    position_counter = Counter(index for item in questions for index in item["answer"])
    total = sum(position_counter.values())
    print("正解位置（全体）:", {label: f"{position_counter[index]}({position_counter[index] / total * 100:.0f}%)"
                           for index, label in enumerate("ABCD")})
    single_counter = Counter(item["answer"][0] for item in questions if item["type"] == "single")
    single_total = sum(single_counter.values())
    print("正解位置（単一のみ）:", {label: f"{single_counter[index]}({single_counter[index] / single_total * 100:.0f}%)"
                              for index, label in enumerate("ABCD")})

    print("単一選択で正解が最長の割合（理想は約25%）:")
    for chapter, (hit, count) in longest_answer_ratio(questions).items():
        print(f"  第{chapter}章: {hit}/{count} ({hit / count * 100:.0f}%)")

    pairs = find_duplicates(questions)
    print(f"重複候補（類似度{SIMILARITY_THRESHOLD}以上）: {len(pairs)}組")
    by_id = {item["id"]: item for item in questions}
    for score, left_id, right_id in pairs[:40]:
        print(f"  {score:.2f} {left_id} / {right_id}")
        print(f"     {by_id[left_id]['question'][:60]}")
        print(f"     {by_id[right_id]['question'][:60]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
