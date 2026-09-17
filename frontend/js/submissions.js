import { getSubmissions, createSubmission } from "./api.js";
import { escapeHtml } from "./utils.js";

const STATUS_LABELS = {
  pending: "Ожидает проверки",
  checked: "Проверено",
  needs_revision: "Нужны исправления",
  accepted: "Принято",
};

function findName(list, id, field) {
  const item = list.find((x) => x.id === id);
  return item ? escapeHtml(item[field]) : `#${id}`;
}

export async function refreshSubmissions(students, labs) {
  const submissions = await getSubmissions();
  const tbody = document.querySelector("#submissions-table tbody");
  tbody.innerHTML = submissions
    .map(
      (s) => `
      <tr>
        <td>${findName(students, s.student_id, "full_name")}</td>
        <td>${findName(labs, s.lab_id, "title")}</td>
        <td>${escapeHtml(s.filename)}</td>
        <td>${STATUS_LABELS[s.status] ?? escapeHtml(s.status)}</td>
        <td>
          <details>
            <summary>Показать вывод</summary>
            <pre>${escapeHtml(s.checker_output)}</pre>
          </details>
        </td>
        <td>${new Date(s.created_at).toLocaleString("ru-RU")}</td>
      </tr>`
    )
    .join("");
}

export function initSubmissionForm(onSubmitted) {
  const form = document.getElementById("upload-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append("student_id", document.getElementById("student-select").value);
    formData.append("lab_id", document.getElementById("lab-select").value);
    formData.append("file", document.getElementById("file-input").files[0]);

    await createSubmission(formData);
    form.reset();
    await onSubmitted();
  });
}
