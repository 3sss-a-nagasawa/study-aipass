"""問題データ（JSON）の検証スクリプト。

使い方:
    python validate.py ..\\data\\chapter3-pilot.json

確認内容:
    1. 必須項目の有無と型
    2. 選択肢が4つで、重複がないこと
    3. 正解の添字が範囲内で、重複がないこと
    4. 単一選択は正解1つ、複数選択は正解2つ以上であること
    5. 正解位置（A〜D）の分布（偏りの確認）
    6. 問題IDの重複
"""
import json
import sys
from collections import Counter

REQUIRED_KEYS = [
    "id", "chapter", "section", "type", "question",
    "choices", "answer", "explanation", "verifiedAt", "volatile",
]
LABELS = ["A", "B", "C", "D"]


def validate_question(question):
    """1問分を検証し、問題点のリストを返す。"""
    problems = []
    for key in REQUIRED_KEYS:
        if key not in question:
            problems.append(f"必須項目 {key} がありません")
    if problems:
        return problems

    choices = question["choices"]
    answer = question["answer"]

    if len(choices) != 4:
        problems.append(f"選択肢が{len(choices)}個です（4個必要）")
    if len(set(choices)) != len(choices):
        problems.append("選択肢に重複があります")
    if question["type"] not in ("single", "multiple"):
        problems.append(f"type が不正です: {question['type']}")
    if any((not isinstance(index, int)) or index < 0 or index >= len(choices) for index in answer):
        problems.append("正解の添字が範囲外です")
    if len(set(answer)) != len(answer):
        problems.append("正解の添字に重複があります")
    if question["type"] == "single" and len(answer) != 1:
        problems.append("単一選択なのに正解が1つではありません")
    if question["type"] == "multiple" and len(answer) < 2:
        problems.append("複数選択なのに正解が2つ未満です")
    return problems


def main():
    if len(sys.argv) != 2:
        print("使い方: python validate.py <JSONファイル>")
        return 1

    with open(sys.argv[1], encoding="utf-8") as file:
        data = json.load(file)

    questions = data["questions"]
    has_error = False

    # 問題IDの重複確認
    id_counter = Counter(question.get("id") for question in questions)
    for question_id, count in id_counter.items():
        if count > 1:
            print(f"[エラー] ID {question_id} が{count}回出現します")
            has_error = True

    # 各問題の検証
    for question in questions:
        for problem in validate_question(question):
            print(f"[エラー] {question.get('id')}: {problem}")
            has_error = True

    # 正解位置の分布
    position_counter = Counter()
    for question in questions:
        for index in question.get("answer", []):
            if isinstance(index, int) and 0 <= index < 4:
                position_counter[index] += 1

    total = sum(position_counter.values())
    single_count = sum(1 for question in questions if question.get("type") == "single")
    print(f"問題数: {len(questions)}（単一選択 {single_count} / 複数選択 {len(questions) - single_count}）")
    print("正解位置の分布（全正解の合計）:")
    for index, label in enumerate(LABELS):
        count = position_counter[index]
        ratio = count / total * 100 if total else 0
        print(f"  {label}: {count} ({ratio:.0f}%)")

    # 偏りの警告（理想の25%から15ポイント以上離れた場合）
    for index, label in enumerate(LABELS):
        ratio = position_counter[index] / total * 100 if total else 0
        if abs(ratio - 25) >= 15:
            print(f"[警告] 正解位置 {label} に偏りがあります（{ratio:.0f}%）")

    # 連続して同じ位置になっていないかの確認（単一選択のみ、3問以上連続で警告）
    single_answers = [question["answer"][0] for question in questions if question.get("type") == "single"]
    run_length = 1
    for current, previous in zip(single_answers[1:], single_answers):
        run_length = run_length + 1 if current == previous else 1
        if run_length >= 3:
            print("[警告] 単一選択で同じ位置の正解が3問以上連続しています")
            break

    print("検証結果:", "エラーあり" if has_error else "問題なし")
    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
