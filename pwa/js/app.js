/**
 * 画面の描画と操作（ハッシュによる画面切り替え）。
 * 問題データ・APIキー・履歴は端末内のみで扱い、Gemini 以外へは送信しない。
 */
(function () {
  "use strict";

  const LETTERS = "ABCD";
  const view = document.getElementById("view");
  const messageBox = document.getElementById("message");
  let questionsCache = null;

  /** 要素を作る小さな補助関数（文字列は textContent で入れ、HTML として解釈しない）。 */
  function el(tag, props, ...children) {
    const node = document.createElement(tag);
    Object.entries(props || {}).forEach(([key, value]) => {
      if (value === undefined || value === null || value === false) return;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key === "style") Object.assign(node.style, value); // CSP 対策で属性ではなく CSSOM で設定
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : value);
    });
    children.flat(Infinity).forEach((child) => {
      if (child === null || child === undefined || child === false) return;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return node;
  }

  /** 画面上部にメッセージを表示する（空文字で消す）。 */
  function showMessage(text) {
    messageBox.textContent = text || "";
    messageBox.hidden = !text;
  }

  /** 画面を差し替える。 */
  function render(...nodes) {
    view.replaceChildren(...nodes);
    window.scrollTo(0, 0);
  }

  function go(hash) {
    if (location.hash === hash) route();
    else location.hash = hash;
  }

  /** 端末内の問題データを、IDをキーにした辞書で返す（未取り込みなら null）。 */
  function getQuestions() {
    if (questionsCache) return questionsCache;
    const data = AppStorage.loadQuestions();
    if (!data) return null;
    try {
      questionsCache = Quiz.indexQuestions(data);
    } catch (error) {
      showMessage("保存されている問題データが壊れています。取り込み直してください。");
      return null;
    }
    return questionsCache;
  }

  /** 受験中の試験を返す。問題データと合わない場合は破棄する。 */
  function getExam() {
    const exam = AppStorage.loadCurrentExam();
    const questions = getQuestions();
    if (!exam || !questions) return null;
    if (exam.items.some((item) => !questions[item.questionId])) {
      AppStorage.clearCurrentExam();
      return null;
    }
    return exam;
  }

  function percent(correct, total) {
    return total ? Math.round((correct / total) * 100) : 0;
  }

  function formatDate(iso) {
    const date = new Date(iso);
    const pad = (value) => String(value).padStart(2, "0");
    return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }

  /** JSON ファイルを選ばせて中身を返す。 */
  function pickJsonFile(onLoad) {
    const input = el("input", { type: "file", accept: ".json,application/json" });
    input.addEventListener("change", () => {
      const file = input.files[0];
      if (!file) return;
      file.text().then((text) => {
        try {
          onLoad(JSON.parse(text), file.name);
        } catch (error) {
          showMessage(error instanceof SyntaxError ? "JSON として読み込めませんでした" : error.message);
        }
      });
    });
    input.click();
  }

  /** 問題データの取り込み。 */
  function importQuestions() {
    pickJsonFile((data, fileName) => {
      const indexed = Quiz.indexQuestions(data);
      // 保存容量を抑えるため questions 配列だけを保存する
      AppStorage.saveQuestions({ questions: Object.values(indexed) }, fileName);
      questionsCache = indexed;
      AppStorage.clearCurrentExam();
      showMessage(`${Object.keys(indexed).length}問を取り込みました`);
      route();
    });
  }

  // ---------- 各画面 ----------

  function renderHome() {
    const meta = AppStorage.questionsMeta();
    const questions = getQuestions();
    const exam = getExam();
    const settings = AppStorage.loadSettings();
    const inProgress = exam && Quiz.currentIndex(exam) !== -1;

    if (!questions) {
      return render(el("section", { class: "card" },
        el("h1", { text: "はじめに" }),
        el("p", { text: "問題データ（all.json）を端末に取り込んでください。データはこの端末の中だけに保存され、サーバーには送信されません。" }),
        el("button", { class: "button primary block", text: "問題データを取り込む", onclick: importQuestions })));
    }

    render(
      el("section", { class: "card" },
        el("h1", { text: "模擬試験" }),
        el("ul", {},
          el("li", { text: `全章からランダムに ${settings.questionCount} 問を出題します。` }),
          el("li", { text: "1問ごとに回答すると、その場で正誤を判定します。" }),
          el("li", { text: "回答後に前の問題へ戻って回答し直すことはできません。" }),
          el("li", { text: "最後に正誤一覧と、AIによる総評を表示します。" })),
        inProgress && el("a", { class: "button block", href: "#question", text: `受験中の試験を続ける（${Quiz.answeredCount(exam)}/${exam.items.length}）` }),
        el("button", { class: "button primary block", text: inProgress ? "最初から新しい試験を始める" : "試験を開始する", onclick: startExam }),
        el("p", { class: "muted", text: `問題データ: ${meta ? meta.count : Object.keys(questions).length}問` }),
        !settings.apiKey && el("p", { class: "muted", text: "AI総評を使うには「設定」でAPIキーを入力してください。" })));
  }

  function startExam() {
    const questions = getQuestions();
    const settings = AppStorage.loadSettings();
    if (!questions) return go("#home");
    const exam = Quiz.createExam(questions, settings.questionCount);
    AppStorage.saveCurrentExam(exam);
    showMessage("");
    go("#question");
  }

  /** 問題番号・進捗・問題文の共通部分。 */
  function questionHeader(exam, index, question) {
    const answered = Quiz.answeredCount(exam);
    return [
      el("div", { class: "progress" },
        el("span", { text: `第 ${index + 1} 問 / ${exam.items.length} 問` }),
        el("span", { class: "muted", text: `正解 ${Quiz.correctCount(exam)} / 回答 ${answered}` })),
      el("div", { class: "progress-bar" }, el("div", { style: { width: `${(answered / exam.items.length) * 100}%` } })),
      el("p", { class: "muted", text: `第${question.chapter}章 ${question.syllabusRef} ${question.section} ／ ${question.type === "multiple" ? "複数選択" : "単一選択"}` }),
      el("p", { class: "question-text", text: question.question }),
    ];
  }

  function renderQuestion() {
    const exam = getExam();
    if (!exam) return go("#home");
    const index = Quiz.currentIndex(exam);
    if (index === -1) return go("#result");
    const item = exam.items[index];
    const question = getQuestions()[item.questionId];
    const inputType = question.type === "multiple" ? "checkbox" : "radio";

    const form = el("form", {},
      el("ul", { class: "choices" }, item.choiceOrder.map((original, display) =>
        el("li", {}, el("label", { class: "choice" },
          el("input", { type: inputType, name: "choice", value: String(display) }),
          el("span", { class: "choice-label", text: LETTERS[display] }),
          el("span", { class: "text", text: question.choices[original] }))))),
      el("button", { type: "submit", class: "button primary block", text: "回答する" }));

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const selected = [...form.querySelectorAll("input:checked")].map((input) => Number(input.value));
      try {
        Quiz.submitAnswer(exam, getQuestions(), index, selected);
      } catch (error) {
        return showMessage(error.message);
      }
      AppStorage.saveCurrentExam(exam);
      showMessage("");
      go(`#judged/${index}`);
    });

    render(el("section", { class: "card" }, questionHeader(exam, index, question), form));
  }

  /** 判定済みの選択肢一覧（正解・自分の回答に印を付ける）。 */
  function judgedChoices(question, item) {
    return el("ul", { class: "choices" }, item.choiceOrder.map((original, display) => {
      const isAnswer = question.answer.includes(original);
      const isSelected = item.selected.includes(original);
      const classes = ["choice", "judged", isAnswer && "is-answer", isSelected && !isAnswer && "is-wrong-pick"].filter(Boolean);
      return el("li", { class: classes.join(" ") },
        el("span", { class: "choice-label", text: LETTERS[display] }),
        el("span", { class: "text", text: question.choices[original] }),
        el("span", {},
          isSelected && el("span", { class: "tag", text: "あなたの回答" }),
          isAnswer && el("span", { class: "tag answer", text: "正解" })));
    }));
  }

  function renderJudged(index) {
    const exam = getExam();
    if (!exam) return go("#home");
    const item = exam.items[index];
    if (!item || item.selected === null) return go("#question");
    const question = getQuestions()[item.questionId];
    const finished = Quiz.currentIndex(exam) === -1;
    render(el("section", { class: "card" },
      questionHeader(exam, index, question),
      el("p", { class: `verdict ${item.isCorrect ? "correct" : "wrong"}`, text: item.isCorrect ? "○ 正解" : "× 不正解" }),
      judgedChoices(question, item),
      el("div", { class: "explanation" }, el("h3", { text: "解説" }), el("p", { text: question.explanation })),
      el("a", { class: "button primary block", href: finished ? "#result" : "#question", text: finished ? "結果を見る" : "次の問題へ" })));
  }

  /** 章別・形式別・中項目別の正答率の表。 */
  function statsSection(summary) {
    const groups = [["章別", summary.byChapter, false], ["形式別", summary.byType, false], ["中項目別", summary.bySection, true]];
    return el("section", { class: "card" }, el("h2", { text: "分野別の正答率" }),
      groups.map(([title, rows, showKey]) => [
        el("h3", { text: title }),
        el("table", { class: "stats" }, rows.map((row) => el("tr", {},
          el("th", { text: (showKey ? row.key + " " : "") + row.label }),
          el("td", { text: `${row.correct}/${row.total}` }),
          el("td", { class: "bar-cell" }, el("div", { class: "bar", style: { width: `${row.rate}%` } })),
          el("td", { text: `${row.rate}%` })))),
      ]));
  }

  function scoreSection(title, total, correct) {
    return el("section", { class: "card" },
      el("h1", { text: title }),
      el("p", { class: "score-value" }, `${total}問中 `, el("strong", { text: String(correct) }), "問正解"),
      el("p", { class: "muted", text: `正答率 ${percent(correct, total)}%` }));
  }

  function renderResult() {
    const exam = getExam();
    if (!exam) return go("#home");
    if (Quiz.currentIndex(exam) !== -1) return go("#question");
    const questions = getQuestions();
    const summary = Quiz.summarize(exam, questions);
    const settings = AppStorage.loadSettings();

    // 試験単位のスコアを履歴に保存（総評は生成後に追記）
    const existing = AppStorage.loadHistory().find((record) => record.examId === exam.examId);
    const record = existing || {
      examId: exam.examId, finishedAt: new Date().toISOString(),
      total: summary.total, correct: summary.correct,
      byChapter: summary.byChapter, bySection: summary.bySection, byType: summary.byType,
      feedback: null, model: null,
    };
    if (!existing) AppStorage.saveHistoryRecord(record);

    const feedbackBody = el("div", { class: "feedback-text" });
    const retryButton = el("button", { class: "button", text: "総評を生成する", hidden: true });

    async function loadFeedback() {
      retryButton.hidden = true;
      if (exam.feedback) return (feedbackBody.textContent = exam.feedback);
      if (!settings.apiKey) {
        feedbackBody.textContent = "APIキーが未設定です。「設定」で入力後、この画面で生成できます。";
        retryButton.hidden = false;
        return;
      }
      feedbackBody.textContent = "総評を生成しています…";
      try {
        const payload = Feedback.buildPayload(exam, questions, summary);
        exam.feedback = await Feedback.generateFeedback(settings.apiKey, settings.model, payload);
        AppStorage.saveCurrentExam(exam);
        AppStorage.saveHistoryRecord(Object.assign(record, { feedback: exam.feedback, model: settings.model }));
        feedbackBody.textContent = exam.feedback;
      } catch (error) {
        feedbackBody.textContent = error.message;
        retryButton.textContent = "再試行する";
        retryButton.hidden = false;
      }
    }
    retryButton.addEventListener("click", () => {
      Object.assign(settings, AppStorage.loadSettings());
      loadFeedback();
    });

    const review = el("section", { class: "card" }, el("h2", { text: "正誤一覧" }),
      exam.items.map((item, index) => {
        const question = questions[item.questionId];
        const texts = (list) => list.map((choice) => question.choices[choice]).join(" ／ ");
        return el("details", { class: `review ${item.isCorrect ? "correct" : "wrong"}`, open: !item.isCorrect },
          el("summary", {},
            el("span", { class: "mark", text: item.isCorrect ? "○" : "×" }),
            `第${index + 1}問　`,
            el("span", { class: "muted", text: `第${question.chapter}章 ${question.syllabusRef} ${question.section}` })),
          el("p", { class: "question-text", text: question.question }),
          el("p", {}, el("strong", { text: "あなたの回答：" }), texts(item.selected)),
          !item.isCorrect && el("p", {}, el("strong", { text: "正解：" }), texts(question.answer)),
          !item.isCorrect && el("div", { class: "explanation" },
            el("h3", { text: "なぜ間違いか" }), el("p", { text: question.explanation })));
      }));

    render(
      scoreSection("試験結果", summary.total, summary.correct),
      el("section", { class: "card" }, el("h2", { text: "AIによる総評" }), feedbackBody, retryButton),
      statsSection(summary),
      review,
      el("button", { class: "button primary block", text: "もう一度受験する", onclick: startExam }));
    loadFeedback();
  }

  function renderHistoryList() {
    const records = AppStorage.loadHistory();
    render(el("section", { class: "card" },
      el("h1", { text: "受験履歴" }),
      records.length === 0
        ? el("p", { class: "muted", text: "まだ受験履歴はありません。" })
        : el("ul", { class: "history-list" }, records.map((record) =>
          el("li", {}, el("a", { href: `#history/${encodeURIComponent(record.examId)}` },
            el("span", { text: formatDate(record.finishedAt) }),
            el("span", { text: `${record.correct}/${record.total}（${percent(record.correct, record.total)}%）${record.feedback ? "" : " 総評なし"}` })))))));
  }

  function renderHistoryDetail(examId) {
    const record = AppStorage.loadHistory().find((item) => item.examId === examId);
    if (!record) return go("#history");
    render(
      scoreSection(`受験結果（${formatDate(record.finishedAt)}）`, record.total, record.correct),
      el("section", { class: "card" }, el("h2", { text: "AIによる総評" }),
        record.feedback
          ? [el("div", { class: "feedback-text", text: record.feedback }), el("p", { class: "muted", text: `モデル: ${record.model}` })]
          : el("p", { class: "muted", text: "総評は保存されていません。" })),
      statsSection(record),
      el("a", { class: "button block", href: "#history", text: "履歴一覧へ戻る" }));
  }

  // 設定画面は settings.js で定義し、ここから呼び出す
  window.AppUI = { el, render, showMessage, go, importQuestions, pickJsonFile, resetQuestionsCache: () => (questionsCache = null) };

  /** ハッシュに応じて画面を切り替える。 */
  function route() {
    const [name, param] = location.hash.replace(/^#/, "").split("/");
    switch (name) {
      case "question": return renderQuestion();
      case "judged": return renderJudged(Number(param));
      case "result": return renderResult();
      case "history": return param ? renderHistoryDetail(decodeURIComponent(param)) : renderHistoryList();
      case "settings": return window.renderSettings ? window.renderSettings() : renderHome();
      default: return renderHome();
    }
  }

  window.addEventListener("hashchange", () => {
    showMessage("");
    route();
  });
  window.addEventListener("load", () => {
    route();
    // オフライン対応（HTTPS または localhost でのみ有効）
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("sw.js").catch(() => { /* 未対応環境では何もしない */ });
    }
    // 端末のデータが自動で消されにくくなるよう永続化を要求する
    if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
  });
})();
