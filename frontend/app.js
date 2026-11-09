"use strict";

const API = "/api";
const KEYS = { student: "labchecker.studentKey", teacher: "labchecker.teacherToken" };

const STATUS = {
  pending: { label: "Ожидает", tone: "neutral" },
  checked: { label: "На проверке", tone: "info" },
  needs_revision: { label: "На доработку", tone: "warn" },
  accepted: { label: "Принято", tone: "ok" },
};
const LANG = { python: "Python", bash: "Bash" };

const store = {
  get(key) {
    try {
      return localStorage.getItem(key) || "";
    } catch {
      return "";
    }
  },
  set(key, value) {
    try {
      if (value) localStorage.setItem(key, value);
      else localStorage.removeItem(key);
    } catch {
    }
  },
};

const state = {
  studentKey: store.get(KEYS.student),
  teacherToken: store.get(KEYS.teacher),
  me: null,
  labs: [],
  mySubmissions: [],
  selectedLabId: null,
  tab: "queue",
};

function h(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (key === "dataset") Object.assign(node.dataset, value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

const $ = (id) => document.getElementById(id);

async function api(path, { method = "GET", json, form, auth } = {}) {
  const headers = {};
  const mode = auth || (state.teacherToken ? "teacher" : "student");
  if (mode === "teacher" && state.teacherToken) headers["X-Teacher-Token"] = state.teacherToken;
  if (mode === "student" && state.studentKey) headers["X-Student-Key"] = state.studentKey;
  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = form;
  }
  const res = await fetch(API + path, { method, headers, body });
  let data = null;
  try {
    data = await res.json();
  } catch {
  }
  if (!res.ok) {
    let detail = data && data.detail;
    if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join("; ");
    const err = new Error(detail || `Ошибка сервера (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}

let toastTimer;
function toast(message, tone = "ok") {
  const box = $("toast");
  box.textContent = message;
  box.dataset.tone = tone;
  box.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (box.hidden = true), 3500);
}

const dateFmt = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});
const formatDate = (iso) => dateFmt.format(new Date(iso));

function plural(n, one, few, many) {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return `${n} ${one}`;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return `${n} ${few}`;
  return `${n} ${many}`;
}

function pill(status) {
  const s = STATUS[status] || { label: status, tone: "neutral" };
  return h("span", { class: `pill pill-${s.tone}`, text: s.label });
}

function showView(name) {
  $("loading").hidden = true;
  for (const view of ["guest", "student", "teacher"]) {
    $(`${view}-view`).hidden = view !== name;
  }
}

function setUser(role, name) {
  $("user-box").hidden = !role;
  $("user-role").textContent = role || "";
  $("user-name").textContent = name || "";
}

function emptyState(text) {
  return h("div", { class: "empty", text });
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

// flake8:     file.py:3:1: F401 'os' imported but unused
// shellcheck: In file.sh line 2: ... ^-- SC2086 (info): ...
function parseIssues(output) {
  const issues = new Map();
  const add = (line, msg) => {
    if (!issues.has(line)) issues.set(line, []);
    issues.get(line).push(msg);
  };
  let shLine = null;
  for (const raw of (output || "").split("\n")) {
    const flake = raw.match(/:(\d+):\d+:\s+([A-Z]+\d+\s.*)$/);
    if (flake) {
      add(Number(flake[1]), flake[2]);
      continue;
    }
    const where = raw.match(/^In .+ line (\d+):\s*$/);
    if (where) {
      shLine = Number(where[1]);
      continue;
    }
    const sc = raw.match(/\^[-^]*\s*(SC\d+.*)$/);
    if (sc && shLine !== null) add(shLine, sc[1]);
  }
  return issues;
}

function codeView(source, output) {
  const lines = (source || "").replace(/\n$/, "").split("\n");
  const issues = parseIssues(output);
  const rows = [];
  lines.forEach((text, i) => {
    const n = i + 1;
    const msgs = issues.get(n);
    rows.push(
      h(
        "div",
        { class: msgs ? "code-line has-issue" : "code-line" },
        h("span", { class: "code-num", text: String(n) }),
        h("span", { class: "code-text", text: text || " " })
      )
    );
    if (msgs) {
      for (const msg of msgs) rows.push(h("div", { class: "code-issue", text: msg }));
    }
  });
  const extra = [...issues.entries()]
    .filter(([n]) => n > lines.length)
    .flatMap(([n, msgs]) => msgs.map((m) => `строка ${n}: ${m}`));
  return h(
    "div",
    { class: "code-wrap" },
    h("div", { class: "code", role: "region", "aria-label": "Код решения", tabindex: "0" }, rows),
    extra.length ? h("ul", { class: "code-extra" }, extra.map((t) => h("li", { text: t }))) : null
  );
}

function linterBlock(submission) {
  const clean = submission.checker_output === "Проблем не найдено.";
  return h(
    "details",
    { class: "linter" },
    h("summary", { text: clean ? "Линтер: замечаний нет" : "Полный вывод линтера" }),
    h("pre", { text: submission.checker_output || "" })
  );
}

function commentBlock(submission) {
  if (!submission.teacher_comment) return null;
  return h(
    "div",
    { class: "comment" },
    h("div", { class: "comment-label", text: "Комментарий преподавателя" }),
    h("div", { class: "comment-text", text: submission.teacher_comment })
  );
}

async function enterStudent() {
  const [me, labs, subs] = await Promise.all([
    api("/me", { auth: "student" }),
    api("/labs", { auth: "student" }),
    api("/me/submissions", { auth: "student" }),
  ]);
  state.me = me;
  state.labs = [...labs].sort((a, b) => a.id - b.id);
  state.mySubmissions = subs;
  if (!state.selectedLabId && labs.length) {
    const pending = labs.find((l) => latestFor(l.id)?.status !== "accepted");
    state.selectedLabId = (pending || labs[0]).id;
  }
  setUser("Студент", me.full_name);
  showView("student");
  renderStudent();
}

function attemptsFor(labId) {
  return state.mySubmissions.filter((s) => s.lab_id === labId);
}

function latestFor(labId) {
  return attemptsFor(labId)[0] || null;
}

function renderStudent() {
  const firstName = state.me.full_name.split(/\s+/)[1] || state.me.full_name;
  $("student-greeting").textContent = `Привет, ${firstName}!`;
  const accepted = state.labs.filter((l) => latestFor(l.id)?.status === "accepted").length;
  $("student-summary").textContent = state.labs.length
    ? `Принято ${accepted} из ${plural(state.labs.length, "лабы", "лаб", "лаб")}`
    : "";

  const grid = $("lab-grid");
  if (!state.labs.length) {
    grid.replaceChildren(emptyState("Преподаватель ещё не добавил ни одной лабы."));
    $("lab-detail").replaceChildren();
    return;
  }

  grid.replaceChildren(
    ...state.labs.map((lab) => {
      const latest = latestFor(lab.id);
      const count = attemptsFor(lab.id).length;
      return h(
        "button",
        {
          type: "button",
          class: lab.id === state.selectedLabId ? "lab-card selected" : "lab-card",
          "aria-pressed": lab.id === state.selectedLabId ? "true" : "false",
          onclick: () => {
            state.selectedLabId = lab.id;
            renderStudent();
            $("lab-detail").scrollIntoView({ behavior: "smooth", block: "start" });
          },
        },
        h(
          "div",
          { class: "lab-card-head" },
          h("span", { class: "lab-title", text: lab.title }),
          h("span", { class: "lang", text: LANG[lab.language] || lab.language })
        ),
        latest ? pill(latest.status) : h("span", { class: "pill pill-neutral", text: "Не сдано" }),
        h("span", { class: "lab-meta", text: count ? plural(count, "попытка", "попытки", "попыток") : "Ещё нет попыток" }),
        latest?.teacher_comment
          ? h("span", { class: "lab-comment", text: `«${latest.teacher_comment}»` })
          : null
      );
    })
  );
  renderLabDetail();
}

function renderLabDetail() {
  const lab = state.labs.find((l) => l.id === state.selectedLabId);
  const box = $("lab-detail");
  if (!lab) {
    box.replaceChildren();
    return;
  }
  const attempts = attemptsFor(lab.id);

  const input = h("input", {
    type: "file",
    class: "visually-hidden",
    id: "file-input",
    accept: lab.language === "python" ? ".py,text/x-python,text/plain" : ".sh,text/x-sh,text/plain",
  });
  const dropText = h("span", {
    class: "drop-text",
    text: `Перетащите файл ${lab.language === "python" ? ".py" : ".sh"} сюда или нажмите, чтобы выбрать`,
  });
  const drop = h(
    "label",
    { class: "drop", for: "file-input" },
    h("span", { class: "drop-icon", "aria-hidden": "true", text: "⬆" }),
    dropText,
    h("span", { class: "drop-hint", text: "Проверка начнётся сразу" }),
    input
  );

  const upload = async (file) => {
    if (!file) return;
    drop.classList.add("busy");
    dropText.textContent = `Проверяю ${file.name}…`;
    const form = new FormData();
    form.append("lab_id", String(lab.id));
    form.append("file", file);
    try {
      const sub = await api("/submissions", { method: "POST", form, auth: "student" });
      state.mySubmissions.unshift(sub);
      toast(sub.status === "checked" ? "Замечаний нет, работа отправлена преподавателю" : "Линтер нашёл замечания", sub.status === "checked" ? "ok" : "warn");
      renderStudent();
    } catch (err) {
      toast(err.message, "error");
      drop.classList.remove("busy");
      dropText.textContent = "Не получилось, попробуйте ещё раз";
    }
  };

  input.addEventListener("change", () => upload(input.files[0]));
  for (const evt of ["dragenter", "dragover"]) {
    drop.addEventListener(evt, (e) => {
      e.preventDefault();
      drop.classList.add("over");
    });
  }
  for (const evt of ["dragleave", "drop"]) {
    drop.addEventListener(evt, () => drop.classList.remove("over"));
  }
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    upload(e.dataTransfer.files[0]);
  });

  box.replaceChildren(
    h(
      "article",
      { class: "card detail" },
      h(
        "div",
        { class: "detail-head" },
        h("h2", { text: lab.title }),
        h("span", { class: "lang", text: LANG[lab.language] || lab.language })
      ),
      lab.description ? h("p", { class: "description", text: lab.description }) : null,
      drop,
      h("h3", { class: "section-title", text: attempts.length ? "Попытки" : "Попыток пока нет" }),
      attempts.map((sub, i) =>
        h(
          "details",
          { class: "attempt", open: i === 0 },
          h(
            "summary",
            {},
            h("span", { class: "attempt-title", text: `Попытка ${attempts.length - i}` }),
            h("span", { class: "attempt-meta", text: `${sub.filename} · ${formatDate(sub.created_at)}` }),
            pill(sub.status)
          ),
          commentBlock(sub),
          codeView(sub.source_code, sub.checker_output),
          linterBlock(sub)
        )
      )
    )
  );
}

const teacher = { students: [], labs: [], submissions: [] };

async function enterTeacher() {
  await api("/auth/check", { auth: "teacher" });
  setUser("Преподаватель", "");
  showView("teacher");
  await loadTeacherData();
  selectTab(state.tab);
}

async function loadTeacherData() {
  const [students, labs, submissions] = await Promise.all([
    api("/students", { auth: "teacher" }),
    api("/labs", { auth: "teacher" }),
    api("/submissions", { auth: "teacher" }),
  ]);
  Object.assign(teacher, { students, labs, submissions });
  const waiting = submissions.filter((s) => s.status === "checked").length;
  $("queue-count").textContent = waiting ? String(waiting) : "";
}

function selectTab(name) {
  state.tab = name;
  for (const tab of document.querySelectorAll(".tab")) {
    const active = tab.dataset.tab === name;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  }
  for (const panel of document.querySelectorAll(".tab-panel")) {
    panel.hidden = panel.dataset.panel !== name;
  }
  if (name === "queue") renderQueue();
  if (name === "students") renderStudents();
  if (name === "labs") renderLabs();
}

function renderQueue() {
  const filter = $("queue-filter").value;
  const items = teacher.submissions.filter((s) => !filter || s.status === filter);
  const list = $("queue-list");
  if (!items.length) {
    list.replaceChildren(emptyState(filter === "checked" ? "Очередь пуста" : "Сдач с таким статусом нет."));
    return;
  }
  list.replaceChildren(...items.map(reviewCard));
}

function reviewCard(sub) {
  const comment = h("textarea", {
    rows: "2",
    placeholder: "Комментарий студенту (необязательно)",
    "aria-label": "Комментарий студенту",
  });
  comment.value = sub.teacher_comment || "";

  const act = async (status, button) => {
    button.disabled = true;
    try {
      const updated = await api(`/submissions/${sub.id}`, {
        method: "PATCH",
        json: { status, teacher_comment: comment.value },
        auth: "teacher",
      });
      Object.assign(sub, updated);
      toast(status === "accepted" ? `Принято: ${sub.student_name}` : `Возвращено: ${sub.student_name}`);
      await loadTeacherData();
      renderQueue();
    } catch (err) {
      toast(err.message, "error");
      button.disabled = false;
    }
  };

  const accept = h("button", { type: "button", class: "btn btn-ok", text: "Принять" });
  const reject = h("button", { type: "button", class: "btn btn-warn", text: "Вернуть на доработку" });
  accept.addEventListener("click", () => act("accepted", accept));
  reject.addEventListener("click", () => act("needs_revision", reject));

  return h(
    "article",
    { class: "card review" },
    h(
      "div",
      { class: "review-head" },
      h(
        "div",
        {},
        h("div", { class: "review-who", text: sub.student_name }),
        h("div", { class: "review-meta", text: `${sub.lab_title} · ${sub.filename} · ${formatDate(sub.created_at)}` })
      ),
      pill(sub.status)
    ),
    codeView(sub.source_code, sub.checker_output),
    linterBlock(sub),
    h("div", { class: "review-actions" }, comment, h("div", { class: "btn-row" }, reject, accept))
  );
}

function showInvite(student, key) {
  const link = `${location.origin}/?key=${encodeURIComponent(key)}`;
  const field = h("input", { type: "text", readonly: true, value: link, "aria-label": "Ссылка студента" });
  const copy = h("button", { type: "button", class: "btn btn-primary", text: "Скопировать" });
  copy.addEventListener("click", async () => {
    if (await copyText(link)) toast("Ссылка скопирована");
    else {
      field.select();
      toast("Скопируйте вручную: Ctrl+C", "warn");
    }
  });
  const box = $("invite-box");
  box.replaceChildren(
    h("div", { class: "invite-title", text: `Ссылка для: ${student.full_name}` }),
    h("div", { class: "invite-row" }, field, copy),
    h("p", {
      class: "muted small",
      text: "Отправьте её студенту лично (например, в Telegram). Ссылка показывается один раз, если потеряется, выпустите новую.",
    })
  );
  box.hidden = false;
  field.focus();
  field.select();
}

function renderStudents() {
  const tbody = document.querySelector("#students-table tbody");
  if (!teacher.students.length) {
    tbody.replaceChildren(h("tr", {}, h("td", { colspan: "5" }, emptyState("Студентов пока нет"))));
    return;
  }
  tbody.replaceChildren(
    ...teacher.students.map((st) => {
      const subs = teacher.submissions.filter((s) => s.student_id === st.id);
      const acceptedLabs = new Set(subs.filter((s) => s.status === "accepted").map((s) => s.lab_id));
      const regen = h("button", { type: "button", class: "btn btn-ghost btn-sm", text: "Новая ссылка" });
      regen.addEventListener("click", async () => {
        if (!confirm(`Выпустить новую ссылку для «${st.full_name}»? Старая перестанет работать.`)) return;
        try {
          const { invite_key } = await api(`/students/${st.id}/invite`, { method: "POST", auth: "teacher" });
          showInvite(st, invite_key);
        } catch (err) {
          toast(err.message, "error");
        }
      });
      return h(
        "tr",
        {},
        h("td", { class: "strong", text: st.full_name }),
        h("td", { class: "muted", text: st.telegram_username ? `@${st.telegram_username.replace(/^@/, "")}` : "—" }),
        h("td", { class: "num", text: String(subs.length) }),
        h("td", { class: "num", text: `${acceptedLabs.size} / ${teacher.labs.length}` }),
        h("td", { class: "actions" }, regen)
      );
    })
  );
}

function renderLabs() {
  const list = $("labs-list");
  if (!teacher.labs.length) {
    list.replaceChildren(emptyState("Лаб пока нет"));
    return;
  }
  list.replaceChildren(
    ...teacher.labs.map((lab) => {
      const subs = teacher.submissions.filter((s) => s.lab_id === lab.id);
      const accepted = new Set(subs.filter((s) => s.status === "accepted").map((s) => s.student_id)).size;
      return h(
        "article",
        { class: "card lab-row" },
        h(
          "div",
          { class: "detail-head" },
          h("h3", { text: lab.title }),
          h("span", { class: "lang", text: LANG[lab.language] || lab.language })
        ),
        lab.description ? h("p", { class: "description", text: lab.description }) : null,
        h("div", { class: "lab-meta", text: `Сдач: ${subs.length} · Приняли: ${accepted} из ${teacher.students.length}` })
      );
    })
  );
}

document.querySelectorAll(".tab").forEach((tab) =>
  tab.addEventListener("click", () => selectTab(tab.dataset.tab))
);
$("queue-filter").addEventListener("change", renderQueue);

$("student-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const st = await api("/students", {
      method: "POST",
      auth: "teacher",
      json: {
        full_name: $("student-name").value.trim(),
        telegram_username: $("student-tg").value.trim().replace(/^@/, "") || null,
      },
    });
    e.target.reset();
    await loadTeacherData();
    renderStudents();
    showInvite(st, st.invite_key);
  } catch (err) {
    toast(err.message, "error");
  }
});

$("lab-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/labs", {
      method: "POST",
      auth: "teacher",
      json: {
        title: $("lab-title").value.trim(),
        language: $("lab-language").value,
        description: $("lab-description").value.trim() || null,
      },
    });
    e.target.reset();
    toast("Лаба добавлена");
    await loadTeacherData();
    renderLabs();
  } catch (err) {
    toast(err.message, "error");
  }
});

const dialog = $("teacher-dialog");
$("open-teacher-login").addEventListener("click", () => {
  $("login-error").hidden = true;
  dialog.showModal();
  $("token-input").focus();
});
$("login-cancel").addEventListener("click", () => dialog.close());

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const token = $("token-input").value.trim();
  state.teacherToken = token;
  try {
    await enterTeacher();
    store.set(KEYS.teacher, token);
    $("token-input").value = "";
    dialog.close();
  } catch (err) {
    state.teacherToken = "";
    $("login-error").textContent = err.status === 401 ? "Неверный токен" : err.message;
    $("login-error").hidden = false;
    showView("guest");
  }
});

$("logout-button").addEventListener("click", () => {
  if (state.teacherToken) {
    state.teacherToken = "";
    store.set(KEYS.teacher, "");
  } else {
    if (!confirm("Выйти? Чтобы войти снова, понадобится ваша личная ссылка.")) return;
    state.studentKey = "";
    store.set(KEYS.student, "");
  }
  start();
});

function takeKeyFromUrl() {
  const url = new URL(location.href);
  const key = url.searchParams.get("key");
  if (!key) return;
  state.studentKey = key;
  store.set(KEYS.student, key);
  url.searchParams.delete("key");
  history.replaceState(null, "", url.pathname + url.search + url.hash);
}

async function start() {
  setUser(null);
  $("guest-error").hidden = true;
  try {
    if (state.teacherToken) {
      try {
        await enterTeacher();
        return;
      } catch (err) {
        if (err.status !== 401) throw err;
        state.teacherToken = "";
        store.set(KEYS.teacher, "");
      }
    }
    if (state.studentKey) {
      try {
        await enterStudent();
        return;
      } catch (err) {
        if (err.status !== 401) throw err;
        state.studentKey = "";
        store.set(KEYS.student, "");
        $("guest-error").textContent = "Ссылка недействительна. Попросите у преподавателя новую.";
        $("guest-error").hidden = false;
      }
    }
    showView("guest");
  } catch (err) {
    $("loading").hidden = false;
    $("loading").textContent = `Не удалось загрузить: ${err.message}`;
  }
}

takeKeyFromUrl();
start();
