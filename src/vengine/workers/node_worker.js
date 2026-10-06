const fs = require("fs");
const childProcess = require("child_process");
const payload = JSON.parse(fs.readFileSync(0, "utf8"));
const spec = payload.spec;
const answer = payload.response;
let output;
try {
  let passed = 0;
  const details = [];
  if (spec.protocol === "function") {
    const originalLog = console.log;
    console.log = () => {};
    try {
      const fn = new Function(`${answer}\nreturn ${spec.entrypoint};`)();
      for (const test of spec.cases) {
        let ok = false;
        try {
          const args = Array.isArray(test.input) ? test.input : [test.input];
          ok = JSON.stringify(fn(...args)) === JSON.stringify(test.expected);
        } catch (_) {}
        if (ok) passed++;
        if (test.visible) details.push({ passed: ok });
      }
    } finally {
      console.log = originalLog;
    }
  } else {
    for (const test of spec.cases) {
      const run = childProcess.spawnSync(process.execPath, ["-e", answer], {
        input: String(test.input),
        encoding: "utf8",
        timeout: 2000,
        maxBuffer: 65536,
      });
      const ok =
        run.status === 0 && run.stdout.trim() === String(test.expected).trim();
      if (ok) passed++;
      if (test.visible) details.push({ passed: ok });
    }
  }
  const score = spec.cases.length ? passed / spec.cases.length : null;
  output = {
    outcome:
      score === 1
        ? "correct"
        : score
          ? "partial"
          : score === 0
            ? "incorrect"
            : "ungraded",
    score,
    feedback: "",
    details: { visible_cases: details },
  };
} catch (error) {
  output = {
    outcome: "error",
    score: null,
    feedback: String(error).slice(0, 200),
    details: {},
  };
}
process.stdout.write(JSON.stringify(output));
