const API_BASE = "http://127.0.0.1:5001/api/todos";

const form = document.getElementById("todo-form");
const input = document.getElementById("todo-input");
const list = document.getElementById("todo-list");
const errorMessage = document.getElementById("error-message");

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.classList.remove("hidden");
}

function clearError() {
  errorMessage.classList.add("hidden");
}

async function apiFetch(url, options) {
  let res;
  try {
    res = await fetch(url, options);
  } catch (err) {
    throw new Error("서버에 연결할 수 없습니다. 백엔드(python app.py)가 실행 중인지 확인하세요.");
  }
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body.error ? `: ${body.error}` : "";
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(`요청 실패 (${res.status})${detail}`);
  }
  return res;
}

async function fetchTodos() {
  try {
    const res = await apiFetch(API_BASE);
    const todos = await res.json();
    clearError();
    renderTodos(todos);
  } catch (err) {
    showError(err.message);
  }
}

function renderTodos(todos) {
  list.innerHTML = "";

  if (todos.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = "할 일이 없습니다.";
    list.appendChild(empty);
    return;
  }

  for (const todo of todos) {
    const item = document.createElement("li");
    item.className = "todo-item" + (todo.done ? " done" : "");

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(todo.done);
    checkbox.addEventListener("change", () => toggleTodo(todo));

    const text = document.createElement("span");
    text.textContent = todo.title;

    const deleteBtn = document.createElement("button");
    deleteBtn.textContent = "삭제";
    deleteBtn.addEventListener("click", () => deleteTodo(todo.id));

    item.append(checkbox, text, deleteBtn);
    list.appendChild(item);
  }
}

async function createTodo(title) {
  try {
    await apiFetch(API_BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    await fetchTodos();
  } catch (err) {
    showError(err.message);
  }
}

async function toggleTodo(todo) {
  try {
    await apiFetch(`${API_BASE}/${todo.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ done: !todo.done }),
    });
    await fetchTodos();
  } catch (err) {
    showError(err.message);
  }
}

async function deleteTodo(id) {
  try {
    await apiFetch(`${API_BASE}/${id}`, { method: "DELETE" });
    await fetchTodos();
  } catch (err) {
    showError(err.message);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const title = input.value.trim();
  if (!title) return;
  input.value = "";
  await createTodo(title);
});

fetchTodos();
