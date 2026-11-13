/**
 * 端末内（localStorage）への保存。問題データ・APIキー・履歴はサーバーへ送らない。
 */
(function (root) {
  "use strict";

  const KEYS = {
    questions: "aipass.questions",
    questionsMeta: "aipass.questionsMeta",
    settings: "aipass.settings",
    currentExam: "aipass.currentExam",
    history: "aipass.history",
  };
  const DEFAULT_SETTINGS = { apiKey: "", model: "gemini-3.5-flash-lite", questionCount: 60 };

  /** JSON を読み込む（無い・壊れている・使えない場合は fallback）。 */
  function readJson(key, fallback) {
    try {
      const text = root.localStorage.getItem(key);
      return text === null ? fallback : JSON.parse(text);
    } catch (error) {
      return fallback;
    }
  }

  /** JSON を書き込む。容量超過などは利用者向けのメッセージで例外にする。 */
  function writeJson(key, value) {
    try {
      root.localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      throw new Error("端末への保存に失敗しました（容量不足またはプライベートブラウズの可能性）");
    }
  }

  function remove(key) {
    try {
      root.localStorage.removeItem(key);
    } catch (error) {
      /* 削除できなくても致命的ではない */
    }
  }

  const Storage = {
    /** 問題データ（all.json の中身）を保存する。 */
    saveQuestions(data, fileName) {
      writeJson(KEYS.questions, data);
      const count = (Array.isArray(data) ? data : data.questions).length;
      writeJson(KEYS.questionsMeta, { count: count, fileName: fileName, importedAt: new Date().toISOString() });
    },
    loadQuestions() {
      return readJson(KEYS.questions, null);
    },
    questionsMeta() {
      return readJson(KEYS.questionsMeta, null);
    },
    clearQuestions() {
      remove(KEYS.questions);
      remove(KEYS.questionsMeta);
    },

    /** 設定（APIキー・モデル・出題数）。 */
    loadSettings() {
      return Object.assign({}, DEFAULT_SETTINGS, readJson(KEYS.settings, {}));
    },
    saveSettings(settings) {
      writeJson(KEYS.settings, Object.assign({}, DEFAULT_SETTINGS, settings));
    },

    /** 受験中の試験（消えても問題ない）。 */
    loadCurrentExam() {
      return readJson(KEYS.currentExam, null);
    },
    saveCurrentExam(exam) {
      writeJson(KEYS.currentExam, exam);
    },
    clearCurrentExam() {
      remove(KEYS.currentExam);
    },

    /** 受験履歴（試験ごとのスコアとAI総評）。新しい順。 */
    loadHistory() {
      return readJson(KEYS.history, []);
    },
    saveHistoryRecord(record) {
      const records = Storage.loadHistory().filter((item) => item.examId !== record.examId);
      records.unshift(record);
      writeJson(KEYS.history, records);
    },
    replaceHistory(records) {
      writeJson(KEYS.history, records);
    },
  };

  root.AppStorage = Storage;
})(self);
