/**
 * Gemini API による総評生成。端末（ブラウザ）から Gemini へ直接送信する。
 * 送信内容: 集計、全問の問題文、誤答した問題の選択肢・回答・正解（解説は送らない）。
 */
(function (root) {
  "use strict";

  const ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/";

  /** Gemini に渡すデータを作る。 */
  function buildPayload(exam, questions, summary) {
    const pick = (row) => ({ label: row.label, correct: row.correct, total: row.total, rate: row.rate });
    return {
      total: summary.total,
      correct: summary.correct,
      by_chapter: summary.byChapter.map(pick),
      by_type: summary.byType.map(pick),
      answers: exam.items.map((item, index) => {
        const question = questions[item.questionId];
        const entry = {
          no: index + 1,
          syllabusRef: question.syllabusRef,
          section: question.section,
          type: question.type === "multiple" ? "複数選択" : "単一選択",
          volatile: Boolean(question.volatile),
          correct: Boolean(item.isCorrect),
          question: question.question,
        };
        if (!item.isCorrect) {
          entry.choices = question.choices;
          entry.selected = (item.selected || []).map((choice) => question.choices[choice]);
          entry.answer = question.answer.map((choice) => question.choices[choice]);
        }
        return entry;
      }),
    };
  }

  /** 総評を依頼するプロンプトを作る（Flask 版 feedback.py と同じ内容）。 */
  function buildPrompt(payload) {
    return (
      "あなたは「生成AIパスポート」（GUGA、2027年2月試験〜の新シラバス）の学習コーチです。\n" +
      "以下は受験者の模擬試験の結果データ（JSON）です。全問の問題文と正誤、" +
      "誤答した問題には選択肢・受験者の回答・正解が含まれます。\n" +
      "このデータに基づき、日本語で次の構成のフィードバックを書いてください。\n" +
      "【総評】合格の目安（正答率約8割）との比較を含めて3〜4文。\n" +
      "【得意な分野】正答率の高い章・中項目。\n" +
      "【苦手な分野】正答率の低い章・中項目と、誤答が集中している論点。\n" +
      "【誤答の傾向】誤答した問題の回答内容から読み取れる誤解のパターン" +
      "（用語の混同、「不適切なもの」を選ぶ問題での読み違い、複数選択での選び漏れ・選び過ぎなど）。" +
      "具体的な問題番号を挙げてよい。\n" +
      "【次の学習アドバイス】優先順位をつけた具体的な学習の進め方を3〜5項目。\n" +
      "見出しは【】で示し、Markdown記法（#、**、表）は使わないでください。" +
      "データから言えないことは推測で書かないでください。\n\n" +
      JSON.stringify(payload)
    );
  }

  /** Gemini API を呼び出して総評テキストを返す。 */
  async function generateFeedback(apiKey, model, payload) {
    if (!apiKey) throw new Error("APIキーが設定されていません（設定画面で入力してください）");
    let response;
    try {
      response = await fetch(ENDPOINT + encodeURIComponent(model) + ":generateContent", {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },
        body: JSON.stringify({ contents: [{ parts: [{ text: buildPrompt(payload) }] }] }),
      });
    } catch (error) {
      throw new Error("Gemini API に接続できませんでした（通信状態を確認してください）");
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = (data.error && data.error.message) || response.statusText;
      throw new Error(`Gemini API の呼び出しに失敗しました（${response.status}）: ${message}`);
    }
    const parts = (((data.candidates || [])[0] || {}).content || {}).parts || [];
    const text = parts.map((part) => part.text || "").join("").trim();
    if (!text) throw new Error("Gemini から空の応答が返りました");
    return text;
  }

  const Feedback = { buildPayload, buildPrompt, generateFeedback };
  if (typeof module !== "undefined" && module.exports) module.exports = Feedback;
  else root.Feedback = Feedback;
})(typeof self !== "undefined" ? self : globalThis);
