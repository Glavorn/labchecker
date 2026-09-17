import { getLabs, createLab } from "./api.js";
import { escapeHtml } from "./utils.js";

export async function refreshLabs() {
  const labs = await getLabs();
  const select = document.getElementById("lab-select");
  select.innerHTML = labs
    .map((l) => `<option value="${l.id}">${escapeHtml(l.title)} (${l.language})</option>`)
    .join("");
  return labs;
}

export function initLabForm(onChange) {
  const form = document.getElementById("lab-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("lab-title").value.trim();
    const language = document.getElementById("lab-language").value;
    const description = document.getElementById("lab-description").value.trim() || null;
    if (!title) return;

    await createLab({ title, language, description });
    form.reset();
    await onChange();
  });
}
