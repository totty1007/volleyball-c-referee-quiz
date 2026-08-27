/* ============================================================
   C級審判 合格ノック — app.js
   バニラJS単一ファイル。ビルド不要、GitHub Pagesでそのまま公開可能。
   ============================================================ */

(function () {
  "use strict";

  const APP = document.getElementById("app");
  const STORAGE_STATS = "vcRef_stats_v1";      // カテゴリ別 正解/回答数
  const STORAGE_WRONG = "vcRef_wrong_v1";      // これまで間違えた問題ID
  const STORAGE_SIGNAL_BEST = "vcRef_signal_best_v1"; // シグナル認識の自己ベスト
  const STORAGE_FOUL_BEST = "vcRef_foul_best_v1";     // 反則クイズの自己ベスト
  const EXAM_SIZE = 25;
  const EXAM_TIME_SEC = 20 * 60; // 20分
  const PRACTICE_LETTERS = ["A", "B", "C", "D", "E"];
  const SIGNAL_CHOICE_COUNT = 4;
  const FOUL_CHOICE_COUNT = 4;

  let DATA = null;          // questions.json の内容
  let CAT_MAP = {};         // id -> name
  let SIGNALS = null;       // signals.json の内容(取得できない場合はnullのまま)
  let FOULS = null;         // fouls.json の内容(取得できない場合はnullのまま)

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

  // シグナル認識モード専用の状態(通常のクイズとはデータ形状が違うため分離する)
  let sigState = {
    queue: [],       // [{signal, direction, choices:[...], correctIndex}]
    index: 0,
    correctCount: 0,
    mistakes: [],    // signal のリスト
  };

  // 反則クイズ(反則一覧から自動生成)専用の状態
  let foulState = {
    queue: [],       // [{foul, direction, choiceFouls:[...], correctIndex}]
    index: 0,
    correctCount: 0,
    mistakes: [],    // foul のリスト
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
  function loadSignalBest() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_SIGNAL_BEST)) || null;
    } catch (e) {
      return null;
    }
  }
  function saveSignalBest(correctCount, total) {
    try {
      const prev = loadSignalBest();
      if (!prev || correctCount > prev.correct || (correctCount === prev.correct && total > prev.total)) {
        localStorage.setItem(STORAGE_SIGNAL_BEST, JSON.stringify({ correct: correctCount, total: total }));
      }
    } catch (e) {
      /* 保存できなくても結果表示は優先する */
    }
  }
  function loadFoulBest() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_FOUL_BEST)) || null;
    } catch (e) {
      return null;
    }
  }
  function saveFoulBest(correctCount, total) {
    try {
      const prev = loadFoulBest();
      if (!prev || correctCount > prev.correct || (correctCount === prev.correct && total > prev.total)) {
        localStorage.setItem(STORAGE_FOUL_BEST, JSON.stringify({ correct: correctCount, total: total }));
      }
    } catch (e) {
      /* 保存できなくても結果表示は優先する */
    }
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

    // シグナル認識モードは任意機能。取得に失敗してもメインのクイズ機能には
    // 影響させず、ホーム画面でそのモードのカードを無効表示にするだけにする。
    fetch("signals.json", { cache: "no-store" })
      .then(res => {
        if (!res.ok) throw new Error("signals.json の取得に失敗しました");
        return res.json();
      })
      .then(json => {
        SIGNALS = json.signals || [];
        if (state.screen === "home") renderHome();
      })
      .catch(() => {
        SIGNALS = null;
      });

    // 反則一覧・反則クイズも任意機能。取得に失敗してもメインのクイズ機能には
    // 影響させず、ホーム画面でそのカードを無効表示にするだけにする。
    fetch("fouls.json", { cache: "no-store" })
      .then(res => {
        if (!res.ok) throw new Error("fouls.json の取得に失敗しました");
        return res.json();
      })
      .then(json => {
        FOULS = (json.fouls || []).slice();
        if (state.screen === "home") renderHome();
      })
      .catch(() => {
        FOULS = null;
      });
  }

  // ---------------- ホーム画面 ----------------
  function renderHome() {
    state.screen = "home";
    const stats = loadStats();
    const wrongCount = loadWrong().size;
    const signalBest = loadSignalBest();
    const signalReady = Array.isArray(SIGNALS) && SIGNALS.length > 0;
    const signalCardBody = signalReady
      ? (signalBest
          ? `自己ベスト: ${signalBest.correct} / ${signalBest.total} 問。${SIGNALS.length}件の図を一覧で覚えてから、図と名称を当てるクイズに挑戦できます。`
          : `ハンドシグナル${SIGNALS.length}件の図と動作説明の一覧。覚えてから、図を見て名称を当てるクイズに挑戦できます。`)
      : "読み込み中、またはこの端末では利用できません。";

    const foulReady = Array.isArray(FOULS) && FOULS.length >= FOUL_CHOICE_COUNT;
    const foulBest = loadFoulBest();
    const foulCardBody = foulReady
      ? (foulBest
          ? `自己ベスト: ${foulBest.correct} / ${foulBest.total} 問。反則の名称と説明の一覧を見てから、一問一答で覚えられます。`
          : `プレー中の反則を名称と説明でまとめた一覧(${FOULS.length}件)。一覧を見てから、そこから出題される一問一答クイズにも挑戦できます。`)
      : "読み込み中、またはこの端末では利用できません。";

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
        本アプリは個人が作成した<strong>非公式の学習教材</strong>です。(公財)日本バレーボール協会・神奈川県バレーボール協会・相模原バレーボール協会とは無関係です。<strong>C級審判員資格(6人制競技規則・一般共通)の筆記試験対策</strong>を目的としており、コート・ネット高さ・ボール・得点・リベロ制度などは<strong>一般6人制の標準ルールを基準</strong>にしています(実際のC級筆記試験が一般6人制ルールで出題されることは、相模原バレーボール協会提供の実物練習問題で確認済みです)。小学生の試合を実際に運営する際に適用される付録2の特別ルール(コート16m×8m等)とは数値が異なりますのでご注意ください。掲載内容は参考情報であり、正誤の最終確認は必ず最新の公式ルールブック・受験要項で行ってください。「シグナル一覧」の図は、規則書の動作説明文をもとに独自に描き起こしたオリジナルの簡易図であり、公式のイラストそのものではありません。図中の<strong>青い数字バッジ(指の本数)や青い動きの矢印</strong>は覚えやすさのために独自に足したもので、実際のハンドシグナルには含まれません。実際の細かい所作は必ず公式の審判実技マニュアルの図で確認してください。
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
        <button class="mode-card" id="btn-signal" ${signalReady ? "" : "disabled"}>
          <span class="num">MODE 04</span>
          <h2>シグナル一覧＆認識クイズ</h2>
          <p>${signalCardBody}</p>
        </button>
        <button class="mode-card" id="btn-fouls" ${foulReady ? "" : "disabled"}>
          <span class="num">MODE 05</span>
          <h2>反則一覧＆反則クイズ</h2>
          <p>${foulCardBody}</p>
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
    if (signalReady) {
      // まず一覧(学習)を見せ、そこから出題へ進ませる(MODE 05の反則と同じ流れ)。
      document.getElementById("btn-signal").addEventListener("click", renderSignalList);
    }
    if (foulReady) {
      document.getElementById("btn-fouls").addEventListener("click", renderFoulList);
    }
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

  // ---------------- シグナル認識モード ----------------
  // 通常のクイズ(questions.json)とはデータ形状が違うため、専用の画面と
  // 状態(sigState)を用意する。localStorageへの正誤記録(recordAnswer)は
  // カテゴリ別正答率の意味を薄めてしまうため行わず、自己ベストのみ保存する。

  // 図(signal.svg)は学習画面と出題画面で同じものを使う。図中の数字バッジ・
  // ネットなどの文脈・動きの矢印は「どのシグナルかを識別する情報」なので、
  // 出題時にも必要だからである(図に反則名は書かれていない)。
  // 学習と出題の差は、図の表示サイズ(style.css)と、図に添える説明文を
  // HTML側で出すかどうかで付けている。

  // 学習画面: 全シグナルを図＋名称＋動作説明で一覧する。ここから出題へ進む。
  function renderSignalList() {
    state.screen = "signalList";
    const cardsHtml = SIGNALS.map(s => `
      <div class="signal-study-card">
        <div class="signal-study-fig">${s.svg}</div>
        <div class="signal-study-body">
          <p class="mi-q">${escapeHtml(s.name)}</p>
          <p>${escapeHtml(s.hint || "")}</p>
        </div>
      </div>
    `).join("");

    APP.innerHTML = `
      <p class="section-title">ハンドシグナル一覧(${SIGNALS.length}件)</p>
      <div class="notice-banner">
        図は規則書の動作説明文をもとに独自に描き起こした<strong>オリジナルの簡易図</strong>で、公式のイラストそのものではありません。
        指の本数を示す<strong>青い数字バッジ</strong>と<strong>青い動きの矢印</strong>は、覚えやすさのためにこのアプリが独自に足したもので、
        実際のハンドシグナルには含まれません。ネット・フロアー・センターライン・アンテナは、そのシグナルが「何を指しているか」を
        示すために描き添えたものです。実際の細かい所作は必ず公式の審判実技マニュアルの図で確認してください。
      </div>
      <div class="signal-study-list">${cardsHtml}</div>
      <div class="result-actions">
        <button class="btn btn-primary" id="btn-start-signal-quiz">シグナルクイズに挑戦</button>
        <button class="btn btn-ghost" id="btn-back-home">ホームへ戻る</button>
      </div>
    `;

    document.getElementById("btn-back-home").addEventListener("click", renderHome);
    document.getElementById("btn-start-signal-quiz").addEventListener("click", startSignalMode);
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function buildSignalQuestion(signal, pool) {
    const direction = Math.random() < 0.5 ? "toName" : "toPicto";
    const others = shuffle(pool.filter(s => s.id !== signal.id)).slice(0, SIGNAL_CHOICE_COUNT - 1);
    const choiceSignals = shuffle([signal, ...others]);
    const correctIndex = choiceSignals.findIndex(s => s.id === signal.id);
    return { signal, direction, choiceSignals, correctIndex };
  }

  function startSignalMode() {
    if (!Array.isArray(SIGNALS) || SIGNALS.length < SIGNAL_CHOICE_COUNT) return;
    stopTimer();
    const queue = shuffle(SIGNALS).map(sig => buildSignalQuestion(sig, SIGNALS));
    sigState = { queue, index: 0, correctCount: 0, mistakes: [] };
    state.screen = "signalQuiz";
    renderSignalQuestion();
  }

  function renderSignalQuestion() {
    // 注意: item.signal.svg は escapeHtml() を通さずそのまま挿入する。
    // signals.json はユーザー入力ではなく、ビルド時のスクリプト(_gen_signals.py)
    // が生成した信頼できるSVGマークアップであり、意図的にHTMLとして描画する。
    const item = sigState.queue[sigState.index];
    const total = sigState.queue.length;
    const pct = Math.round((sigState.index / total) * 100);

    let bodyHtml;
    if (item.direction === "toName") {
      const choicesHtml = item.choiceSignals.map((s, i) => `
        <button class="choice-btn" data-index="${i}">
          <span class="letter">${PRACTICE_LETTERS[i]}</span>
          <span>${escapeHtml(s.name)}</span>
        </button>
      `).join("");
      bodyHtml = `
        <p class="q-text">このシグナルが示す反則・合図は次のうちどれか。</p>
        <div class="signal-figure-wrap">${item.signal.svg}</div>
        <div class="choices" id="choices">${choicesHtml}</div>
      `;
    } else {
      const thumbsHtml = item.choiceSignals.map((s, i) => `
        <button class="signal-thumb-btn" data-index="${i}">${s.svg}</button>
      `).join("");
      bodyHtml = `
        <p class="q-text">「${escapeHtml(item.signal.name)}」を示す図は次のうちどれか。</p>
        <div class="signal-thumb-grid" id="choices">${thumbsHtml}</div>
      `;
    }

    APP.innerHTML = `
      <div class="quiz-topbar">
        <span>シグナル認識｜問 ${sigState.index + 1} / ${total}</span>
        <span class="quiz-progress-track"><span class="quiz-progress-fill" style="width:${pct}%"></span></span>
      </div>
      <div class="q-card">
        <span class="q-cat-tag">審判員の役割・シグナル</span>
        ${bodyHtml}
        <div id="explanation-slot"></div>
      </div>
      <div class="quiz-nav">
        <button class="btn btn-ghost" id="btn-quit">中断してホームへ</button>
        <button class="btn btn-primary hidden" id="btn-next">${sigState.index + 1 < total ? "次の問題へ" : "結果を見る"}</button>
      </div>
    `;

    document.getElementById("btn-quit").addEventListener("click", renderHome);
    document.querySelectorAll("#choices > button").forEach(btn => {
      btn.addEventListener("click", () => onChooseSignal(parseInt(btn.dataset.index, 10)));
    });
  }

  function onChooseSignal(chosenIndex) {
    const item = sigState.queue[sigState.index];
    const correct = chosenIndex === item.correctIndex;
    const buttons = document.querySelectorAll("#choices > button");

    buttons.forEach((btn, i) => {
      btn.disabled = true;
      if (i === item.correctIndex) btn.classList.add("correct");
      else if (i === chosenIndex) btn.classList.add("incorrect");
    });

    if (correct) {
      sigState.correctCount += 1;
    } else {
      sigState.mistakes.push(item.signal);
    }

    document.getElementById("explanation-slot").innerHTML = `
      <div class="explanation ${correct ? "" : "wrong-tone"}">
        <strong>${correct ? "正解です。" : "不正解。"}</strong>
        正解は「${escapeHtml(item.signal.name)}」。${escapeHtml(item.signal.hint || "")}
      </div>
    `;

    document.getElementById("btn-next").classList.remove("hidden");
    document.getElementById("btn-next").onclick = () => {
      if (sigState.index + 1 < sigState.queue.length) {
        sigState.index += 1;
        renderSignalQuestion();
      } else {
        finishSignalRound();
      }
    };
  }

  function finishSignalRound() {
    state.screen = "signalResult";
    const total = sigState.queue.length;
    const correctCount = sigState.correctCount;
    const pct = total ? Math.round((correctCount / total) * 100) : 0;
    saveSignalBest(correctCount, total);

    const mistakeHtml = sigState.mistakes.length === 0
      ? `<p style="color:var(--muted)">間違えたシグナルはありませんでした。お見事です。</p>`
      : sigState.mistakes.map(s => `
          <div class="mistake-item">
            <div class="signal-figure-wrap" style="max-width:150px;margin:0 0 8px;">${s.svg}</div>
            <p class="mi-q">${escapeHtml(s.name)}</p>
            <p style="color:#4B5A6A;font-size:13px;">${escapeHtml(s.hint || "")}</p>
          </div>
        `).join("");

    APP.innerHTML = `
      <div class="result-board">
        <div class="result-score">${correctCount}<span> / ${total} 問正解</span></div>
        <p class="result-sub">正答率 ${pct}%</p>
      </div>

      <p class="section-title">間違えたシグナル(${sigState.mistakes.length}件)</p>
      <div class="mistake-list">${mistakeHtml}</div>

      <div class="result-actions">
        <button class="btn btn-primary" id="btn-signal-retry">もう一度挑戦する</button>
        <button class="btn btn-ghost" id="btn-back-siglist">シグナル一覧を見る</button>
        <button class="btn btn-ghost" id="btn-back-home">ホームへ戻る</button>
      </div>
    `;

    document.getElementById("btn-back-home").addEventListener("click", renderHome);
    document.getElementById("btn-back-siglist").addEventListener("click", renderSignalList);
    document.getElementById("btn-signal-retry").addEventListener("click", startSignalMode);
  }

  // ---------------- 反則一覧＆反則クイズ ----------------
  // fouls.json(反則の名称＋説明の一覧)を①そのまま読み物として表示する画面と、
  // ②その一覧データから自動生成する一問一答クイズの2つを提供する。
  // クイズ問題はquestions.jsonのような静的データではなく、fouls.jsonの
  // name/descriptionから実行時に組み立てる(シグナル認識モードと同じ考え方)。
  function renderFoulList() {
    state.screen = "foulList";
    const cardsHtml = FOULS.map(f => `
      <div class="mistake-item foul-card">
        <p class="mi-q">${escapeHtml(f.name)}</p>
        <p>${escapeHtml(f.description)}</p>
      </div>
    `).join("");

    APP.innerHTML = `
      <p class="section-title">反則一覧(${FOULS.length}件)</p>
      <div class="notice-banner">
        プレー中に起きる主な反則を、名称と説明でまとめた一覧です。questions.jsonの出題・解説と同じ内容を
        再編集したもので、新しい未確認情報は加えていません。下の「反則クイズに挑戦」から、この一覧をもとに
        した一問一答クイズにも挑戦できます。
      </div>
      <div class="mistake-list">${cardsHtml}</div>
      <div class="result-actions">
        <button class="btn btn-primary" id="btn-start-foul-quiz">反則クイズに挑戦</button>
        <button class="btn btn-ghost" id="btn-back-home">ホームへ戻る</button>
      </div>
    `;

    document.getElementById("btn-back-home").addEventListener("click", renderHome);
    document.getElementById("btn-start-foul-quiz").addEventListener("click", startFoulQuiz);
  }

  function buildFoulQuestion(foul, pool) {
    const direction = Math.random() < 0.5 ? "toDesc" : "toName";
    const others = shuffle(pool.filter(f => f.id !== foul.id)).slice(0, FOUL_CHOICE_COUNT - 1);
    const choiceFouls = shuffle([foul, ...others]);
    const correctIndex = choiceFouls.findIndex(f => f.id === foul.id);
    return { foul, direction, choiceFouls, correctIndex };
  }

  function startFoulQuiz() {
    if (!Array.isArray(FOULS) || FOULS.length < FOUL_CHOICE_COUNT) return;
    stopTimer();
    const queue = shuffle(FOULS).map(f => buildFoulQuestion(f, FOULS));
    foulState = { queue, index: 0, correctCount: 0, mistakes: [] };
    state.screen = "foulQuiz";
    renderFoulQuestion();
  }

  function renderFoulQuestion() {
    const item = foulState.queue[foulState.index];
    const total = foulState.queue.length;
    const pct = Math.round((foulState.index / total) * 100);

    let questionText, choicesHtml;
    if (item.direction === "toDesc") {
      questionText = `「${escapeHtml(item.foul.name)}」の説明として正しいものはどれか。`;
      choicesHtml = item.choiceFouls.map((f, i) => `
        <button class="choice-btn" data-index="${i}">
          <span class="letter">${PRACTICE_LETTERS[i]}</span>
          <span>${escapeHtml(f.description)}</span>
        </button>
      `).join("");
    } else {
      questionText = `次の説明にあたる反則の名称として正しいものはどれか。<br>「${escapeHtml(item.foul.description)}」`;
      choicesHtml = item.choiceFouls.map((f, i) => `
        <button class="choice-btn" data-index="${i}">
          <span class="letter">${PRACTICE_LETTERS[i]}</span>
          <span>${escapeHtml(f.name)}</span>
        </button>
      `).join("");
    }

    APP.innerHTML = `
      <div class="quiz-topbar">
        <span>反則クイズ｜問 ${foulState.index + 1} / ${total}</span>
        <span class="quiz-progress-track"><span class="quiz-progress-fill" style="width:${pct}%"></span></span>
      </div>
      <div class="q-card">
        <span class="q-cat-tag">プレー・反則</span>
        <p class="q-text">${questionText}</p>
        <div class="choices" id="choices">${choicesHtml}</div>
        <div id="explanation-slot"></div>
      </div>
      <div class="quiz-nav">
        <button class="btn btn-ghost" id="btn-quit">中断してホームへ</button>
        <button class="btn btn-primary hidden" id="btn-next">${foulState.index + 1 < total ? "次の問題へ" : "結果を見る"}</button>
      </div>
    `;

    document.getElementById("btn-quit").addEventListener("click", renderHome);
    document.querySelectorAll("#choices > button").forEach(btn => {
      btn.addEventListener("click", () => onChooseFoul(parseInt(btn.dataset.index, 10)));
    });
  }

  function onChooseFoul(chosenIndex) {
    const item = foulState.queue[foulState.index];
    const correct = chosenIndex === item.correctIndex;
    const buttons = document.querySelectorAll("#choices > button");

    buttons.forEach((btn, i) => {
      btn.disabled = true;
      if (i === item.correctIndex) btn.classList.add("correct");
      else if (i === chosenIndex) btn.classList.add("incorrect");
    });

    if (correct) {
      foulState.correctCount += 1;
    } else {
      foulState.mistakes.push(item.foul);
    }

    document.getElementById("explanation-slot").innerHTML = `
      <div class="explanation ${correct ? "" : "wrong-tone"}">
        <strong>${correct ? "正解です。" : "不正解。"}</strong>
        「${escapeHtml(item.foul.name)}」: ${escapeHtml(item.foul.description)}
      </div>
    `;

    document.getElementById("btn-next").classList.remove("hidden");
    document.getElementById("btn-next").onclick = () => {
      if (foulState.index + 1 < foulState.queue.length) {
        foulState.index += 1;
        renderFoulQuestion();
      } else {
        finishFoulRound();
      }
    };
  }

  function finishFoulRound() {
    state.screen = "foulResult";
    const total = foulState.queue.length;
    const correctCount = foulState.correctCount;
    const pct = total ? Math.round((correctCount / total) * 100) : 0;
    saveFoulBest(correctCount, total);

    const mistakeHtml = foulState.mistakes.length === 0
      ? `<p style="color:var(--muted)">間違えた反則はありませんでした。お見事です。</p>`
      : foulState.mistakes.map(f => `
          <div class="mistake-item">
            <p class="mi-q">${escapeHtml(f.name)}</p>
            <p style="color:#4B5A6A;font-size:13px;">${escapeHtml(f.description)}</p>
          </div>
        `).join("");

    APP.innerHTML = `
      <div class="result-board">
        <div class="result-score">${correctCount}<span> / ${total} 問正解</span></div>
        <p class="result-sub">正答率 ${pct}%</p>
      </div>

      <p class="section-title">間違えた反則(${foulState.mistakes.length}件)</p>
      <div class="mistake-list">${mistakeHtml}</div>

      <div class="result-actions">
        <button class="btn btn-primary" id="btn-foul-retry">もう一度挑戦する</button>
        <button class="btn btn-ghost" id="btn-back-list">反則一覧を見る</button>
        <button class="btn btn-ghost" id="btn-back-home">ホームへ戻る</button>
      </div>
    `;

    document.getElementById("btn-back-home").addEventListener("click", renderHome);
    document.getElementById("btn-back-list").addEventListener("click", renderFoulList);
    document.getElementById("btn-foul-retry").addEventListener("click", startFoulQuiz);
  }

  // ---------------- 起動 ----------------
  document.addEventListener("DOMContentLoaded", init);
})();
