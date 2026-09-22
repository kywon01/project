const API_BASE = "http://localhost:5000/api/todos";

const form = document.getElementById("todo-form");
const input = document.getElementById("todo-input");
const list = document.getElementById("todo-list");

async function fetchTodos() {
  const res = await fetch(API_BASE);
  const todos = await res.json();
  renderTodos(todos);
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
  await fetch(API_BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  await fetchTodos();
}

async function toggleTodo(todo) {
  await fetch(`${API_BASE}/${todo.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ done: !todo.done }),
  });
  await fetchTodos();
}

async function deleteTodo(id) {
  await fetch(`${API_BASE}/${id}`, { method: "DELETE" });
  await fetchTodos();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const title = input.value.trim();
  if (!title) return;
  input.value = "";
  await createTodo(title);
});

fetchTodos();
