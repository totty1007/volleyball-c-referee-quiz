/* ============================================================
   C級審判 合格ノック — app.js
   バニラJS単一ファイル。ビルド不要、GitHub Pagesでそのまま公開可能。
   ============================================================ */

(function () {
  "use strict";

  const APP = document.getElementById("app");
  const STORAGE_STATS = "vcRef_stats_v1";      // カテゴリ別 正解/回答数
  const STORAGE_WRONG = "vcRef_wrong_v1";      // これまで間違えた問題ID
  const EXAM_SIZE = 25;
  const EXAM_TIME_SEC = 20 * 60; // 20分
  const PRACTICE_LETTERS = ["A", "B", "C", "D", "E"];

  let DATA = null;          // questions.json の内容
  let CAT_MAP = {};         // id -> name

  let state = {
    screen: "loading",
    mode: null,             // 'practice' | 'exam' | 'review'
    selectedCats: new Set(),
    queue: [],
    index: 0,
    answers: [],            // {id, correct, chosenIndex}
    timerId: null,
    remainingSec: 0,
  };

  // ---------------- ユーティリティ ----------------
  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function loadStats() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_STATS)) || {};
    } catch (e) {
      return {};
    }
  }
  function saveStats(stats) {
    // プライベートブラウジングや容量超過時に setItem が例外を投げることがある。
    // ここで失敗しても、次の問題への遷移など他の処理は止めない(記録だけ諦める)。
    try {
      localStorage.setItem(STORAGE_STATS, JSON.stringify(stats));
    } catch (e) {
      /* 保存できなくても学習の続行は優先する */
    }
  }
  function loadWrong() {
    try {
      return new Set(JSON.parse(localStorage.getItem(STORAGE_WRONG)) || []);
    } catch (e) {
      return new Set();
    }
  }
  function saveWrong(set) {
    try {
      localStorage.setItem(STORAGE_WRONG, JSON.stringify(Array.from(set)));
    } catch (e) {
      /* 保存できなくても学習の続行は優先する */
    }
  }
  function recordAnswer(question, correct) {
    const stats = loadStats();
    if (!stats[question.category]) stats[question.category] = { correct: 0, total: 0 };
    stats[question.category].total += 1;
    if (correct) stats[question.category].correct += 1;
    saveStats(stats);

    const wrong = loadWrong();
    if (correct) {
      wrong.delete(question.id);
    } else {
      wrong.add(question.id);
    }
    saveWrong(wrong);
  }
  function escapeHtml(value) {
    // questions.json は自分たちで管理するデータとはいえ、将来的な自動更新
    // (スクレイピング等)や表記ゆれ("<"や"&"を含む条文引用など)で
    // 表示が崩れたり意図しないHTMLとして解釈されたりしないよう、
    // 動的に挿入するテキストは必ずエスケープする。
    if (value === undefined || value === null) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }
  function formatTime(sec) {
    const m = Math.floor(sec / 60).toString().padStart(2, "0");
    const s = Math.floor(sec % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  }
  function globalAccuracy() {
    const stats = loadStats();
    let c = 0, t = 0;
    Object.values(stats).forEach(s => { c += s.correct; t += s.total; });
    if (t === 0) return null;
    return Math.round((c / t) * 100);
  }
  function updateHeaderStat() {
    const el = document.getElementById("global-stat-value");
    const acc = globalAccuracy();
    el.textContent = acc === null ? "--%" : `${acc}%`;
  }

  // ---------------- データ読み込み ----------------
  function init() {
    fetch("questions.json", { cache: "no-store" })
      .then(res => {
        if (!res.ok) throw new Error("questions.json の取得に失敗しました");
        return res.json();
      })
      .then(json => {
        DATA = json;
        CAT_MAP = {};
        DATA.categories.forEach(c => (CAT_MAP[c.id] = c.name));
        document.getElementById("footer-updated").textContent =
          DATA.meta && DATA.meta.lastUpdated ? DATA.meta.lastUpdated : "-";
        state.selectedCats = new Set(DATA.categories.map(c => c.id));
        updateHeaderStat();
        renderHome();
      })
      .catch(err => {
        APP.innerHTML = `<div class="empty-state">
          <p>問題データの読み込みに失敗しました。</p>
          <p style="font-size:12px;color:var(--muted)">${err.message}</p>
        </div>`;
      });
  }

  // ---------------- ホーム画面 ----------------
  function renderHome() {
    state.screen = "home";
    const stats = loadStats();
    const wrongCount = loadWrong().size;

    const catPills = DATA.categories.map(c => {
      const n = DATA.questions.filter(q => q.category === c.id).length;
      const active = state.selectedCats.has(c.id);
      return `<button class="cat-pill ${active ? "active" : ""}" data-cat="${escapeHtml(c.id)}">
        ${escapeHtml(c.name)} <span class="count">${n}</span>
      </button>`;
    }).join("");

    const statBars = DATA.categories.map(c => {
      const s = stats[c.id];
      const pct = s && s.total ? Math.round((s.correct / s.total) * 100) : 0;
      return `<div class="stat-bar-row">
        <span class="cat-name">${escapeHtml(c.name)}</span>
        <span class="stat-bar-track"><span class="stat-bar-fill" style="width:${pct}%"></span></span>
        <span class="stat-bar-pct">${s && s.total ? pct + "%" : "-"}</span>
      </div>`;
    }).join("");

    APP.innerHTML = `
      <div class="notice-banner">
        本アプリは個人が作成した<strong>非公式の学習教材</strong>です。(公財)日本バレーボール協会・神奈川県バレーボール協会・相模原バレーボール協会とは無関係です。掲載内容は参考情報であり、正誤の最終確認は必ず最新の公式ルールブック・受験要項で行ってください。
      </div>
      <div class="mode-grid">
        <button class="mode-card primary" id="btn-exam">
          <span class="num">MODE 01</span>
          <h2>模擬試験</h2>
          <p>本番想定・${EXAM_SIZE}問${Math.round(EXAM_TIME_SEC / 60)}分・合否判定つき。全カテゴリからランダム出題。</p>
        </button>
        <button class="mode-card" id="btn-practice">
          <span class="num">MODE 02</span>
          <h2>演習モード</h2>
          <p>カテゴリを選んでコツコツ演習。1問ごとに解説つきで確認できます。</p>
        </button>
        <button class="mode-card" id="btn-review" ${wrongCount === 0 ? "disabled" : ""}>
          <span class="num">MODE 03</span>
          <h2>苦手問題の復習</h2>
          <p>${wrongCount > 0 ? `過去に間違えた ${wrongCount} 問だけを出題します。` : "間違えた問題はまだありません。"}</p>
        </button>
        <div class="mode-card" style="cursor:default;">
          <span class="num">STATUS</span>
          <h2>学習の記録</h2>
          <p>正答率や間違えた問題数はこの端末(ブラウザ)に保存されます。</p>
        </div>
      </div>

      <p class="section-title">演習モードの出題カテゴリ</p>
      <div class="cat-list" id="cat-list">${catPills}</div>
      <div class="start-actions">
        <button class="btn btn-primary" id="btn-start-practice">選んだカテゴリで演習を始める</button>
        <button class="btn btn-ghost" id="btn-select-all">全選択</button>
      </div>

      <p class="section-title" style="margin-top:34px;">カテゴリ別 正答率</p>
      <div class="breakdown">${statBars}</div>
    `;

    document.getElementById("btn-exam").addEventListener("click", startExam);
    document.getElementById("btn-review").addEventListener("click", startReview);
    document.getElementById("btn-practice").addEventListener("click", () => {
      window.scrollTo({ top: document.getElementById("cat-list").offsetTop - 100, behavior: "smooth" });
    });
    document.getElementById("btn-start-practice").addEventListener("click", () => startPractice());
    document.getElementById("btn-select-all").addEventListener("click", () => {
      state.selectedCats = new Set(DATA.categories.map(c => c.id));
      renderHome();
    });
    document.querySelectorAll(".cat-pill").forEach(btn => {
      btn.addEventListener("click", () => {
        const cat = btn.dataset.cat;
        if (state.selectedCats.has(cat)) {
          if (state.selectedCats.size > 1) state.selectedCats.delete(cat);
        } else {
          state.selectedCats.add(cat);
        }
        renderHome();
      });
    });
  }

  // ---------------- モード開始 ----------------
  function startPractice() {
    const pool = DATA.questions.filter(q => state.selectedCats.has(q.category));
    if (pool.length === 0) return;
    beginQuiz("practice", shuffle(pool));
  }

  function startExam() {
    const pool = shuffle(DATA.questions).slice(0, Math.min(EXAM_SIZE, DATA.questions.length));
    // remainingSec は beginQuiz (→renderQuestion) より前に設定する。
    // 後で設定すると、開始直後の描画で timer が 00:00 のまま一瞬表示されてしまう。
    state.remainingSec = EXAM_TIME_SEC;
    beginQuiz("exam", pool);
    startTimer();
  }

  function startReview() {
    const wrong = loadWrong();
    const pool = DATA.questions.filter(q => wrong.has(q.id));
    if (pool.length === 0) return;
    beginQuiz("review", shuffle(pool));
  }

  function beginQuiz(mode, queue) {
    stopTimer();
    state.mode = mode;
    state.queue = queue;
    state.index = 0;
    state.answers = [];
    state.screen = "quiz";
    renderQuestion();
  }

  function startTimer() {
    stopTimer();
    state.timerId = setInterval(() => {
      state.remainingSec -= 1;
      updateTimerDisplay();
      if (state.remainingSec <= 0) {
        stopTimer();
        finishQuiz();
      }
    }, 1000);
  }
  function stopTimer() {
    if (state.timerId) clearInterval(state.timerId);
    state.timerId = null;
  }
  function updateTimerDisplay() {
    const el = document.getElementById("exam-timer");
    if (!el) return;
    el.textContent = formatTime(Math.max(0, state.remainingSec));
    el.classList.toggle("low", state.remainingSec <= 60);
  }

  // ---------------- クイズ画面 ----------------
  function renderQuestion() {
    const q = state.queue[state.index];
    const total = state.queue.length;
    const pct = Math.round((state.index / total) * 100);

    const modeLabel = { practice: "演習モード", exam: "模擬試験", review: "苦手問題の復習" }[state.mode];

    const timerHtml = state.mode === "exam"
      ? `<span class="timer" id="exam-timer">${formatTime(state.remainingSec)}</span>`
      : "";

    const letters = q.type === "truefalse" ? ["○", "×"] : PRACTICE_LETTERS;
    const choicesHtml = q.choices.map((c, i) => `
      <button class="choice-btn" data-index="${i}">
        <span class="letter">${letters[i] || (i + 1)}</span>
        <span>${escapeHtml(c)}</span>
      </button>
    `).join("");

    const verifyBadge = q.verifyNote
      ? `<span class="verify-tag" title="${escapeHtml(q.verifyNote)}">⚠ 地域・年度で異なる場合あり</span>`
      : "";

    APP.innerHTML = `
      <div class="quiz-topbar">
        <span>${modeLabel}｜問 ${state.index + 1} / ${total}</span>
        <span class="quiz-progress-track"><span class="quiz-progress-fill" style="width:${pct}%"></span></span>
        ${timerHtml}
      </div>
      <div class="q-card">
        <span class="q-cat-tag">${escapeHtml(CAT_MAP[q.category] || "その他")}</span>
        ${verifyBadge}
        <p class="q-text">${escapeHtml(q.question)}</p>
        <div class="choices" id="choices">${choicesHtml}</div>
        <div id="explanation-slot"></div>
      </div>
      <div class="quiz-nav">
        <button class="btn btn-ghost" id="btn-quit">中断してホームへ</button>
        <button class="btn btn-primary hidden" id="btn-next">${state.index + 1 < total ? "次の問題へ" : "結果を見る"}</button>
      </div>
    `;

    document.getElementById("btn-quit").addEventListener("click", () => {
      stopTimer();
      renderHome();
    });

    document.querySelectorAll(".choice-btn").forEach(btn => {
      btn.addEventListener("click", () => onChoose(parseInt(btn.dataset.index, 10)));
    });
  }

  function onChoose(chosenIndex) {
    const q = state.queue[state.index];
    const correct = chosenIndex === q.answer;

    document.querySelectorAll(".choice-btn").forEach((btn, i) => {
      btn.disabled = true;
      if (i === q.answer) btn.classList.add("correct");
      else if (i === chosenIndex) btn.classList.add("incorrect");
    });

    document.getElementById("explanation-slot").innerHTML = `
      <div class="explanation ${correct ? "" : "wrong-tone"}">
        <strong>${correct ? "正解です。" : "不正解。"}</strong> ${escapeHtml(q.explanation)}
        ${q.verifyNote ? `<br><span class="explanation-note">※ ${escapeHtml(q.verifyNote)}</span>` : ""}
      </div>
    `;

    document.getElementById("btn-next").classList.remove("hidden");
    document.getElementById("btn-next").onclick = () => {
      state.answers.push({ id: q.id, category: q.category, correct, chosenIndex });
      recordAnswer(q, correct);
      updateHeaderStat();
      if (state.index + 1 < state.queue.length) {
        state.index += 1;
        renderQuestion();
      } else {
        finishQuiz();
      }
    };
  }

  // ---------------- 結果画面 ----------------
  function finishQuiz() {
    stopTimer();
    state.screen = "result";

    // タイムアップで未回答が残っている場合は不正解として記録
    const answeredIds = new Set(state.answers.map(a => a.id));
    state.queue.forEach(q => {
      if (!answeredIds.has(q.id)) {
        state.answers.push({ id: q.id, category: q.category, correct: false, chosenIndex: -1, unanswered: true });
        recordAnswer(q, false);
      }
    });

    const total = state.answers.length;
    const correctCount = state.answers.filter(a => a.correct).length;
    const pct = total ? Math.round((correctCount / total) * 100) : 0;
    const passLine = (DATA.meta && DATA.meta.passLine) || 70;
    const isExam = state.mode === "exam";
    const passed = pct >= passLine;

    const byCat = {};
    state.answers.forEach(a => {
      if (!byCat[a.category]) byCat[a.category] = { c: 0, t: 0 };
      byCat[a.category].t += 1;
      if (a.correct) byCat[a.category].c += 1;
    });
    const breakdownHtml = Object.keys(byCat).map(catId => {
      const s = byCat[catId];
      const p = Math.round((s.c / s.t) * 100);
      return `<div class="stat-bar-row">
        <span class="cat-name">${escapeHtml(CAT_MAP[catId] || catId)}</span>
        <span class="stat-bar-track"><span class="stat-bar-fill" style="width:${p}%"></span></span>
        <span class="stat-bar-pct">${s.c}/${s.t}</span>
      </div>`;
    }).join("");

    const mistakes = state.answers.filter(a => !a.correct);
    const mistakeHtml = mistakes.length === 0
      ? `<p style="color:var(--muted)">間違えた問題はありませんでした。お見事です。</p>`
      : mistakes.map(a => {
          const q = DATA.questions.find(x => x.id === a.id);
          const yourAns = a.unanswered || a.chosenIndex < 0 ? "(未回答)" : q.choices[a.chosenIndex];
          const badge = q.verifyNote ? `<span class="verify-tag" style="margin:0 0 6px;">⚠ 地域・年度で異なる場合あり</span>` : "";
          return `<div class="mistake-item">
            ${badge}
            <p class="mi-q">${escapeHtml(q.question)}</p>
            <p class="mi-your">あなたの回答: ${escapeHtml(yourAns)}</p>
            <p class="mi-correct">正解: ${escapeHtml(q.choices[q.answer])}</p>
            <p style="color:#4B5A6A;font-size:13px;">${escapeHtml(q.explanation)}</p>
          </div>`;
        }).join("");

    APP.innerHTML = `
      <div class="result-board">
        ${isExam ? `<span class="result-badge ${passed ? "pass" : "fail"}">${passed ? "合格ライン到達" : "合格ラインに届かず"}</span>` : ""}
        <div class="result-score">${correctCount}<span> / ${total} 問正解</span></div>
        <p class="result-sub">正答率 ${pct}%${isExam ? `（合格ラインの目安: ${passLine}%）` : ""}</p>
      </div>

      <p class="section-title">カテゴリ別の結果</p>
      <div class="breakdown">${breakdownHtml}</div>

      <p class="section-title">間違えた問題（${mistakes.length}問）</p>
      <div class="mistake-list">${mistakeHtml}</div>

      <div class="result-actions">
        <button class="btn btn-primary" id="btn-retry-mistakes" ${mistakes.length === 0 ? "disabled" : ""}>間違えた問題だけ復習する</button>
        <button class="btn btn-ghost" id="btn-back-home">ホームへ戻る</button>
      </div>
    `;

    document.getElementById("btn-back-home").addEventListener("click", renderHome);
    document.getElementById("btn-retry-mistakes").addEventListener("click", () => {
      const ids = new Set(mistakes.map(m => m.id));
      const pool = DATA.questions.filter(q => ids.has(q.id));
      beginQuiz("review", shuffle(pool));
    });
  }

  // ---------------- 起動 ----------------
  document.addEventListener("DOMContentLoaded", init);
})();
