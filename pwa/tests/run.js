/**
 * PWA 版ロジックのテスト（外部ライブラリなし。Node 12 以降で動作）。
 * 実行: node pwa/tests/run.js
 */
const assert = require("assert");
const Quiz = require("../js/quiz.js");
const { makeDummyQuestions } = require("./dummy.js");

const tests = [];
function test(name, body) {
  tests.push({ name, body });
}

/** 再現可能な疑似乱数（線形合同法）。 */
function seededRandom(seed) {
  let state = seed;
  return (max) => {
    state = (state * 1103515245 + 12345) % 2147483648;
    return state % max;
  };
}

function setup() {
  const questions = Quiz.indexQuestions(makeDummyQuestions());
  const exam = Quiz.createExam(questions, 60, seededRandom(1));
  return { questions, exam };
}

test("60問が重複なく選ばれ、選択肢の順序が並べ替えであること", () => {
  const { exam } = setup();
  const ids = exam.items.map((item) => item.questionId);
  assert.strictEqual(ids.length, 60);
  assert.strictEqual(new Set(ids).size, 60);
  exam.items.forEach((item) => assert.deepStrictEqual(item.choiceOrder.slice().sort(), [0, 1, 2, 3]));
});

test("シャッフル後も内容に紐づけて正解判定できること", () => {
  const { questions, exam } = setup();
  const item = exam.items[0];
  const selected = questions[item.questionId].answer.map((original) => item.choiceOrder.indexOf(original));
  assert.strictEqual(Quiz.submitAnswer(exam, questions, 0, selected), true);
  assert.strictEqual(Quiz.correctCount(exam), 1);
});

test("再回答と順番飛ばしを拒否すること", () => {
  const { questions, exam } = setup();
  Quiz.submitAnswer(exam, questions, 0, [0]);
  assert.throws(() => Quiz.submitAnswer(exam, questions, 0, [1]));
  assert.throws(() => Quiz.submitAnswer(exam, questions, 5, [1]));
});

test("複数選択はすべて一致した場合のみ正解とすること", () => {
  const question = { type: "multiple", answer: [0, 2] };
  assert.strictEqual(Quiz.gradeAnswer(question, [2, 0]), true);
  assert.strictEqual(Quiz.gradeAnswer(question, [0]), false);
  assert.strictEqual(Quiz.gradeAnswer(question, [0, 1, 2]), false);
});

test("全問回答後に終了状態になり、集計が合うこと", () => {
  const { questions, exam } = setup();
  for (let index = 0; index < 60; index++) Quiz.submitAnswer(exam, questions, index, [0]);
  assert.strictEqual(Quiz.currentIndex(exam), -1);
  const summary = Quiz.summarize(exam, questions);
  assert.strictEqual(summary.byChapter.reduce((sum, row) => sum + row.total, 0), 60);
  assert.strictEqual(summary.correct, Quiz.correctCount(exam));
});

test("形式が不正な問題データを拒否すること", () => {
  assert.throws(() => Quiz.indexQuestions({}));
  assert.throws(() => Quiz.indexQuestions({ questions: [{ id: "x" }] }));
});

let failed = 0;
tests.forEach(({ name, body }) => {
  try {
    body();
    console.log(`OK   ${name}`);
  } catch (error) {
    failed += 1;
    console.log(`NG   ${name}\n     ${error.message}`);
  }
});
console.log(`${tests.length - failed}/${tests.length} 件成功`);
process.exit(failed ? 1 : 0);
