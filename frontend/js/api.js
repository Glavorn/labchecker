const API = "/api";

async function request(path, options) {
  const res = await fetch(`${API}${path}`, options);
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || `Ошибка запроса: ${res.status}`);
  }
  return res.json();
}

export function getStudents() {
  return request("/students");
}

export function createStudent(data) {
  return request("/students", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function getLabs() {
  return request("/labs");
}

export function createLab(data) {
  return request("/labs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function getSubmissions() {
  return request("/submissions");
}

export function createSubmission(formData) {
  return request("/submissions", { method: "POST", body: formData });
}
