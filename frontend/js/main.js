import { refreshStudents, initStudentForm } from "./students.js";
import { refreshLabs, initLabForm } from "./labs.js";
import { refreshSubmissions, initSubmissionForm } from "./submissions.js";

async function refreshAll() {
  const students = await refreshStudents();
  const labs = await refreshLabs();
  await refreshSubmissions(students, labs);
}

initStudentForm(refreshAll);
initLabForm(refreshAll);
initSubmissionForm(refreshAll);

refreshAll();
