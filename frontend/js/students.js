import { getStudents, createStudent } from "./api.js";
import { escapeHtml } from "./utils.js";

export async function refreshStudents() {
  const students = await getStudents();
  const select = document.getElementById("student-select");
  select.innerHTML = students
    .map((s) => `<option value="${s.id}">${escapeHtml(s.full_name)}</option>`)
    .join("");
  return students;
}

export function initStudentForm(onChange) {
  const form = document.getElementById("student-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const full_name = document.getElementById("student-name").value.trim();
    const telegram_username =
      document.getElementById("student-telegram").value.trim() || null;
    if (!full_name) return;

    await createStudent({ full_name, telegram_username });
    form.reset();
    await onChange();
  });
}
