/**
 * 出題・採点・集計のロジック（画面に依存しない）。Flask 版 quiz.py の移植。
 * ブラウザでは window.Quiz、Node（テスト）では module.exports として使う。
 */
(function (root) {
  "use strict";

  /** 0以上 max 未満の乱数整数を返す（暗号論的乱数が使えれば使う）。 */
  function randomInt(max) {
    if (root.crypto && root.crypto.getRandomValues) {
      const buffer = new Uint32Array(1);
      root.crypto.getRandomValues(buffer);
      return buffer[0] % max;
    }
    return Math.floor(Math.random() * max);
  }

  /** 配列をシャッフルした新しい配列を返す（フィッシャー–イェーツ法）。 */
  function shuffle(list, random) {
    const result = list.slice();
    for (let index = result.length - 1; index > 0; index--) {
      const swapIndex = random(index + 1);
      [result[index], result[swapIndex]] = [result[swapIndex], result[index]];
    }
    return result;
  }

  /** 問題データ（all.json の中身）を検証し、IDをキーにした辞書を返す。 */
  function indexQuestions(data) {
    const questions = Array.isArray(data) ? data : data && data.questions;
    if (!Array.isArray(questions) || questions.length === 0) {
      throw new Error("問題データの形式が正しくありません（questions 配列がありません）");
    }
    const byId = {};
    questions.forEach((question) => {
      const required = ["id", "chapter", "type", "question", "choices", "answer", "explanation"];
      required.forEach((key) => {
        if (question[key] === undefined) throw new Error(`問題 ${question.id || "?"} に ${key} がありません`);
      });
      byId[question.id] = question;
    });
    return byId;
  }

  /** 全章から count 問をランダムに選び、選択肢もシャッフルした試験を作る。 */
  function createExam(questions, count, random) {
    random = random || randomInt;
    const ids = shuffle(Object.keys(questions), random).slice(0, count);
    return {
      examId: Date.now().toString(36) + "-" + random(1e9).toString(36),
      startedAt: new Date().toISOString(),
      items: ids.map((id) => ({
        questionId: id,
        choiceOrder: shuffle(questions[id].choices.map((_, index) => index), random),
        selected: null,
        isCorrect: null,
      })),
      feedback: null,
    };
  }

  /** 次に回答すべき問題の添字（全問回答済みなら -1）。 */
  function currentIndex(exam) {
    return exam.items.findIndex((item) => item.selected === null);
  }

  /** 正解数を返す。 */
  function correctCount(exam) {
    return exam.items.filter((item) => item.isCorrect).length;
  }

  /** 回答済みの問題数を返す。 */
  function answeredCount(exam) {
    return exam.items.filter((item) => item.selected !== null).length;
  }

  /** 選択した元の添字が正解と完全一致すれば正解（本試験と同じ）。 */
  function gradeAnswer(question, selectedOriginal) {
    const selected = new Set(selectedOriginal);
    const answer = new Set(question.answer);
    return selected.size === answer.size && [...answer].every((value) => selected.has(value));
  }

  /** 表示順の添字で回答を受け付けて採点する。再回答・順番飛ばしは拒否する。 */
  function submitAnswer(exam, questions, index, selectedDisplay) {
    if (currentIndex(exam) !== index) {
      throw new Error("この問題には回答できません（回答済み、または順番が違います）");
    }
    const item = exam.items[index];
    const question = questions[item.questionId];
    if (!selectedDisplay || selectedDisplay.length === 0) throw new Error("選択肢を選んでください");
    if (selectedDisplay.some((choice) => choice < 0 || choice >= item.choiceOrder.length)) {
      throw new Error("不正な選択肢です");
    }
    if (question.type === "single" && selectedDisplay.length !== 1) throw new Error("選択肢を1つ選んでください");
    item.selected = [...new Set(selectedDisplay.map((choice) => item.choiceOrder[choice]))].sort((a, b) => a - b);
    item.isCorrect = gradeAnswer(question, item.selected);
    return item.isCorrect;
  }

  /** 章別・中項目別・形式別の正答数を集計する。 */
  function summarize(exam, questions) {
    const tables = { byChapter: {}, bySection: {}, byType: {} };
    function add(table, key, label, isCorrect) {
      const row = table[key] || (table[key] = { key: key, label: label, total: 0, correct: 0 });
      row.total += 1;
      row.correct += isCorrect ? 1 : 0;
    }
    exam.items.forEach((item) => {
      const question = questions[item.questionId];
      add(tables.byChapter, String(question.chapter), `第${question.chapter}章`, item.isCorrect);
      add(tables.bySection, question.syllabusRef, question.section, item.isCorrect);
      add(tables.byType, question.type, question.type === "multiple" ? "複数選択" : "単一選択", item.isCorrect);
    });
    function toList(table) {
      return Object.keys(table)
        .sort((a, b) => a.localeCompare(b, "ja", { numeric: true }))
        .map((key) => Object.assign(table[key], { rate: Math.round((table[key].correct / table[key].total) * 100) }));
    }
    return {
      total: exam.items.length,
      correct: correctCount(exam),
      byChapter: toList(tables.byChapter),
      bySection: toList(tables.bySection),
      byType: toList(tables.byType),
    };
  }

  const Quiz = {
    indexQuestions, createExam, currentIndex, correctCount, answeredCount,
    gradeAnswer, submitAnswer, summarize, shuffle,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = Quiz;
  else root.Quiz = Quiz;
})(typeof self !== "undefined" ? self : globalThis);
