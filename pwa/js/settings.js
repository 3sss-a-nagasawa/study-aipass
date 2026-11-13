/**
 * 設定画面: APIキー・モデル・出題数、問題データの取り込み/削除、履歴の書き出し/読み込み。
 */
(function () {
  "use strict";

  /** JSON をファイルとして保存させる（iPhone では共有シートから「ファイル」に保存できる）。 */
  function downloadJson(data, fileName) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  /** 読み込んだ履歴を既存の履歴へ統合する（同じ試験IDは読み込んだ側を優先）。 */
  function importHistory(data) {
    if (!Array.isArray(data) || data.some((record) => !record || !record.examId || record.total === undefined)) {
      throw new Error("履歴ファイルの形式が正しくありません");
    }
    const merged = {};
    AppStorage.loadHistory().concat(data).forEach((record) => (merged[record.examId] = record));
    const records = Object.values(merged).sort((a, b) => (b.finishedAt || "").localeCompare(a.finishedAt || ""));
    AppStorage.replaceHistory(records);
    return data.length;
  }

  window.renderSettings = function () {
    const { el, render, showMessage, importQuestions, pickJsonFile, resetQuestionsCache } = window.AppUI;
    const settings = AppStorage.loadSettings();
    const meta = AppStorage.questionsMeta();

    const apiKeyInput = el("input", { type: "password", autocomplete: "off", value: settings.apiKey, placeholder: "Gemini の APIキー" });
    const modelInput = el("input", { type: "text", autocomplete: "off", value: settings.model });
    const countInput = el("input", { type: "number", min: "1", max: "200", value: String(settings.questionCount) });

    const form = el("form", {},
      el("label", { class: "field" }, "Gemini APIキー（この端末にのみ保存）", apiKeyInput),
      el("label", { class: "field" }, "モデル", modelInput),
      el("label", { class: "field" }, "1回の出題数", countInput),
      el("button", { type: "submit", class: "button primary block", text: "保存する" }));
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const count = Math.max(1, Math.min(200, parseInt(countInput.value, 10) || 60));
      AppStorage.saveSettings({ apiKey: apiKeyInput.value.trim(), model: modelInput.value.trim() || "gemini-3.5-flash-lite", questionCount: count });
      showMessage("設定を保存しました");
      window.scrollTo(0, 0);
    });

    function clearQuestions() {
      if (!confirm("端末内の問題データと受験中の試験を削除します。よろしいですか？")) return;
      AppStorage.clearQuestions();
      AppStorage.clearCurrentExam();
      resetQuestionsCache();
      showMessage("問題データを削除しました");
      window.renderSettings();
    }

    function exportHistory() {
      const stamp = new Date().toISOString().slice(0, 10);
      downloadJson(AppStorage.loadHistory(), `aipass-history-${stamp}.json`);
    }

    function clearHistory() {
      if (!confirm("受験履歴をすべて削除します。よろしいですか？")) return;
      AppStorage.replaceHistory([]);
      showMessage("受験履歴を削除しました");
    }

    render(
      el("section", { class: "card" }, el("h1", { text: "設定" }), form),
      el("section", { class: "card" },
        el("h2", { text: "問題データ" }),
        el("p", { class: "muted", text: meta ? `${meta.count}問（${meta.fileName || "ファイル名不明"}、${new Date(meta.importedAt).toLocaleString("ja-JP")} 取り込み）` : "未取り込み" }),
        el("button", { class: "button", text: "取り込む／入れ替える", onclick: importQuestions }),
        meta && el("button", { class: "button danger", text: "削除する", onclick: clearQuestions })),
      el("section", { class: "card" },
        el("h2", { text: "受験履歴のバックアップ" }),
        el("p", { class: "muted", text: "端末のデータは長期間使わないと消えることがあります。定期的に書き出してください。" }),
        el("button", { class: "button", text: "書き出す", onclick: exportHistory }),
        el("button", { class: "button", text: "読み込む", onclick: () => pickJsonFile((data) => showMessage(`${importHistory(data)}件の履歴を読み込みました`)) }),
        el("button", { class: "button danger", text: "すべて削除", onclick: clearHistory })),
      el("section", { class: "card" },
        el("h2", { text: "データの扱い" }),
        el("p", { class: "muted", text: "問題データ・APIキー・履歴はこの端末のブラウザ内にのみ保存されます。AI総評の生成時のみ、問題文と回答が Gemini API に送信されます。" })));
  };
})();
