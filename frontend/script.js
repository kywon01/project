const API_BASE = "http://127.0.0.1:5001/api/todos";
const CATEGORIES_URL = "http://127.0.0.1:5001/api/categories";

const form = document.getElementById("todo-form");
const input = document.getElementById("todo-input");
const dueDateInput = document.getElementById("due-date-input");
const priorityInput = document.getElementById("priority-input");
const categoryInput = document.getElementById("category-input");
const categoryOptions = document.getElementById("category-options");

const searchInput = document.getElementById("search-input");
const categoryFilter = document.getElementById("category-filter");
const priorityFilter = document.getElementById("priority-filter");

const list = document.getElementById("todo-list");
const errorMessage = document.getElementById("error-message");

const PRIORITY_LABELS = { high: "높음", medium: "보통", low: "낮음" };

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
    throw new Error("서버에 연결할 수 없습니다. 백엔드(python3 app.py)가 실행 중인지 확인하세요.");
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

function buildQuery() {
  const params = new URLSearchParams();
  if (searchInput.value.trim()) params.set("search", searchInput.value.trim());
  if (categoryFilter.value) params.set("category", categoryFilter.value);
  if (priorityFilter.value) params.set("priority", priorityFilter.value);
  const qs = params.toString();
  return qs ? `${API_BASE}?${qs}` : API_BASE;
}

async function fetchTodos() {
  try {
    const res = await apiFetch(buildQuery());
    const todos = await res.json();
    clearError();
    renderTodos(todos);
  } catch (err) {
    showError(err.message);
  }
}

async function fetchCategories() {
  try {
    const res = await apiFetch(CATEGORIES_URL);
    const categories = await res.json();
    populateCategoryOptions(categories);
  } catch {
    // category list is a non-critical enhancement; ignore failures here
  }
}

function populateCategoryOptions(categories) {
  const previousFilterValue = categoryFilter.value;

  categoryFilter.innerHTML = '<option value="">전체 카테고리</option>';
  categoryOptions.innerHTML = "";

  for (const category of categories) {
    const filterOption = document.createElement("option");
    filterOption.value = category;
    filterOption.textContent = category;
    categoryFilter.appendChild(filterOption);

    const dataListOption = document.createElement("option");
    dataListOption.value = category;
    categoryOptions.appendChild(dataListOption);
  }

  if (categories.includes(previousFilterValue)) {
    categoryFilter.value = previousFilterValue;
  }
}

function formatDueDate(dueDate, done) {
  if (!dueDate) return null;
  const isOverdue = !done && dueDate < new Date().toISOString().slice(0, 10);
  const el = document.createElement("span");
  el.className = "due-date" + (isOverdue ? " overdue" : "");
  el.textContent = `마감일: ${dueDate}${isOverdue ? " (지남)" : ""}`;
  return el;
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

    const main = document.createElement("div");
    main.className = "todo-main";

    const title = document.createElement("span");
    title.className = "todo-title";
    title.textContent = todo.title;
    main.appendChild(title);

    const meta = document.createElement("div");
    meta.className = "todo-meta";

    const priorityBadge = document.createElement("span");
    priorityBadge.className = `badge priority-${todo.priority}`;
    priorityBadge.textContent = PRIORITY_LABELS[todo.priority] || todo.priority;
    meta.appendChild(priorityBadge);

    if (todo.category) {
      const categoryBadge = document.createElement("span");
      categoryBadge.className = "badge category-badge";
      categoryBadge.textContent = todo.category;
      meta.appendChild(categoryBadge);
    }

    const dueDateEl = formatDueDate(todo.due_date, todo.done);
    if (dueDateEl) meta.appendChild(dueDateEl);

    if (meta.childElementCount > 0) main.appendChild(meta);

    const deleteBtn = document.createElement("button");
    deleteBtn.textContent = "삭제";
    deleteBtn.addEventListener("click", () => deleteTodo(todo.id));

    item.append(checkbox, main, deleteBtn);
    list.appendChild(item);
  }
}

async function createTodo() {
  try {
    await apiFetch(API_BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: input.value.trim(),
        due_date: dueDateInput.value || null,
        priority: priorityInput.value,
        category: categoryInput.value.trim() || null,
      }),
    });
    await fetchTodos();
    await fetchCategories();
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
    await fetchCategories();
  } catch (err) {
    showError(err.message);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const title = input.value.trim();
  if (!title) return;
  await createTodo();
  form.reset();
  priorityInput.value = "medium";
});

let searchDebounce;
searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(fetchTodos, 300);
});
categoryFilter.addEventListener("change", fetchTodos);
priorityFilter.addEventListener("change", fetchTodos);

fetchTodos();
fetchCategories();
