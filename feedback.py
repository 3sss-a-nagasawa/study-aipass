"""Gemini API による試験結果の総評生成。

利用者の許可に基づき、集計に加えて各問の問題文・選択肢・回答・正解を送信する。
（問題データを GitHub 等へ公開しないルールとは別扱い）
"""

import json


class FeedbackError(Exception):
    """総評を生成できなかったことを表す例外。"""


def build_payload(exam, questions, summary):
    """Gemini に渡す集計データと各問の詳細を作る。"""
    answers = []
    for number, item in enumerate(exam.items, start=1):
        question = questions[item.question_id]
        entry = {
            "no": number,
            "syllabusRef": question["syllabusRef"],
            "section": question["section"],
            "type": "複数選択" if question["type"] == "multiple" else "単一選択",
            "volatile": bool(question.get("volatile")),
            "correct": bool(item.is_correct),
            "question": question["question"],
        }
        # 誤答の分析に使うため、誤答した問題だけ選択肢・回答・正解を付ける（トークン節約）
        if not item.is_correct:
            entry["choices"] = question["choices"]
            entry["selected"] = [question["choices"][index] for index in item.selected or []]
            entry["answer"] = [question["choices"][index] for index in question["answer"]]
        answers.append(entry)
    return {
        "total": summary["total"],
        "correct": summary["correct"],
        "by_chapter": [{k: row[k] for k in ("label", "correct", "total", "rate")} for row in summary["by_chapter"]],
        "by_type": [{k: row[k] for k in ("label", "correct", "total", "rate")} for row in summary["by_type"]],
        "answers": answers,
    }


def build_prompt(payload):
    """総評を依頼するプロンプトを作る。"""
    return (
        "あなたは「生成AIパスポート」（GUGA、2027年2月試験〜の新シラバス）の学習コーチです。\n"
        "以下は受験者の模擬試験の結果データ（JSON）です。全問の問題文と正誤、"
        "誤答した問題には選択肢・受験者の回答・正解が含まれます。\n"
        "このデータに基づき、日本語で次の構成のフィードバックを書いてください。\n"
        "【総評】合格の目安（正答率約8割）との比較を含めて3〜4文。\n"
        "【得意な分野】正答率の高い章・中項目。\n"
        "【苦手な分野】正答率の低い章・中項目と、誤答が集中している論点。\n"
        "【誤答の傾向】誤答した問題の回答内容から読み取れる誤解のパターン"
        "（用語の混同、「不適切なもの」を選ぶ問題での読み違い、複数選択での選び漏れ・選び過ぎなど）。"
        "具体的な問題番号を挙げてよい。\n"
        "【次の学習アドバイス】優先順位をつけた具体的な学習の進め方を3〜5項目。\n"
        "見出しは【】で示し、Markdown記法（#、**、表）は使わないでください。"
        "データから言えないことは推測で書かないでください。\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )


def generate_feedback(api_key, model, payload):
    """Gemini API を呼び出して総評テキストを返す。"""
    if not api_key:
        raise FeedbackError("GEMINI_API_KEY が設定されていません（.env を確認してください）")
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=build_prompt(payload))
    except Exception as error:  # API・通信エラーはまとめて利用者に伝える
        raise FeedbackError(f"Gemini API の呼び出しに失敗しました: {error}") from error
    text = (response.text or "").strip()
    if not text:
        raise FeedbackError("Gemini から空の応答が返りました")
    return text
