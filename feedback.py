"""Gemini API による試験結果の総評生成。

著作権・情報管理への配慮から、問題文・選択肢・解説は送信しない。
送信するのは、正答数の集計と各問のメタ情報（中項目・形式・問われ方・正誤）のみ。
"""

import json


class FeedbackError(Exception):
    """総評を生成できなかったことを表す例外。"""


def build_payload(exam, questions, summary):
    """Gemini に渡す集計データを作る（問題文は含めない）。"""
    answers = []
    for number, item in enumerate(exam.items, start=1):
        question = questions[item.question_id]
        answers.append({
            "no": number,
            "syllabusRef": question["syllabusRef"],
            "section": question["section"],
            "type": "複数選択" if question["type"] == "multiple" else "単一選択",
            # 問題文そのものではなく「不適切なものを選ぶ形式か」だけを渡す
            "asks": "不適切なもの" if "不適切" in question["question"] else "適切なもの",
            "volatile": bool(question.get("volatile")),
            "correct": bool(item.is_correct),
        })
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
        "以下は受験者の模擬試験60問の結果データ（JSON）です。問題文は含まれていません。\n"
        "このデータだけに基づき、日本語で次の構成のフィードバックを書いてください。\n"
        "【総評】合格の目安（正答率約8割）との比較を含めて3〜4文。\n"
        "【得意な分野】正答率の高い章・中項目。\n"
        "【苦手な分野】正答率の低い章・中項目と、誤答が集中している箇所。\n"
        "【回答の傾向】単一/複数選択、「適切/不適切なもの」を選ぶ形式、試験の前半/後半、"
        "変わりやすい内容（volatile）での正誤の傾向。データから言えることだけを書く。\n"
        "【次の学習アドバイス】優先順位をつけた具体的な学習の進め方を3〜5項目。\n"
        "見出しは【】で示し、Markdown記法（#、**、表）は使わないでください。"
        "データにない問題内容を推測して書かないでください。\n\n"
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
