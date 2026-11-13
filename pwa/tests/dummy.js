/** テスト用のダミー問題データ（本物の問題文は使わない）。 */
function makeDummyQuestions(count) {
  const questions = [];
  for (let number = 0; number < (count || 70); number++) {
    const isMultiple = number % 4 === 0;
    questions.push({
      id: "dummy-" + String(number).padStart(3, "0"),
      chapter: (number % 5) + 1,
      section: "ダミー中項目",
      syllabusRef: `${(number % 5) + 1}-1`,
      type: isMultiple ? "multiple" : "single",
      question: `ダミー問題${number}`,
      choices: ["選択肢甲", "選択肢乙", "選択肢丙", "選択肢丁"],
      answer: isMultiple ? [0, 2] : [number % 4],
      explanation: "ダミー解説",
      volatile: false,
    });
  }
  return { questions: questions };
}

module.exports = { makeDummyQuestions };
