const state = {
  query: "",
  tag: "",
  showArchived: false,
  sort: "updated",
};

const noteForm = document.getElementById("note-form");
const notesList = document.getElementById("notes-list");
const statsPanel = document.getElementById("stats-panel");
const searchInput = document.getElementById("search-input");
const tagFilter = document.getElementById("tag-filter");
const showArchived = document.getElementById("show-archived");
const sortSelect = document.getElementById("sort-select");
const noteTemplate = document.getElementById("note-template");

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    let message = "Request failed";
    try {
      const payload = await response.json();
      message = payload.error || message;
    } catch (error) {
      message = `${message} (${response.status})`;
    }
    throw new Error(message);
  }

  return response.status === 204 ? null : response.json();
}

function parseTags(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatTime(iso) {
  return new Date(iso).toLocaleString();
}

function renderStats(stats) {
  statsPanel.innerHTML = `
    <div class="stat-box"><strong>${stats.total}</strong><span>Total</span></div>
    <div class="stat-box"><strong>${stats.active}</strong><span>Active</span></div>
    <div class="stat-box"><strong>${stats.archived}</strong><span>Archived</span></div>
    <div class="stat-box"><strong>${stats.pinned}</strong><span>Pinned</span></div>
  `;
}

function createFlag(text) {
  const span = document.createElement("span");
  span.className = "flag";
  span.textContent = text;
  return span;
}

function renderEmptyState() {
  notesList.innerHTML = `<div class="empty-state">No notes match the current filters.</div>`;
}

function renderNotes(notes) {
  notesList.innerHTML = "";
  if (!notes.length) {
    renderEmptyState();
    return;
  }

  for (const note of notes) {
    const fragment = noteTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".note-card");
    const idNode = fragment.querySelector(".note-id");
    const flagRow = fragment.querySelector(".flag-row");
    const editor = fragment.querySelector(".note-editor");
    const tagEditor = fragment.querySelector(".tag-editor");
    const timeRow = fragment.querySelector(".timestamp-row");
    const saveButton = fragment.querySelector(".save-button");
    const pinButton = fragment.querySelector(".pin-button");
    const archiveButton = fragment.querySelector(".archive-button");
    const deleteButton = fragment.querySelector(".delete-button");

    idNode.textContent = `Note #${note.id}`;
    editor.value = note.text;
    tagEditor.value = (note.tags || []).join(", ");
    timeRow.textContent = `Created ${formatTime(note.created_at)} | Updated ${formatTime(note.updated_at)}`;

    if (note.pinned) {
      flagRow.appendChild(createFlag("Pinned"));
      pinButton.textContent = "Unpin";
    }
    if (note.archived) {
      flagRow.appendChild(createFlag("Archived"));
      archiveButton.textContent = "Restore";
    }
    if (!note.tags.length) {
      flagRow.appendChild(createFlag("No tags"));
    } else {
      note.tags.forEach((tag) => flagRow.appendChild(createFlag(`#${tag}`)));
    }

    saveButton.addEventListener("click", async () => {
      try {
        await request(`/api/notes/${note.id}`, {
          method: "PUT",
          body: JSON.stringify({
            text: editor.value,
            tags: parseTags(tagEditor.value),
          }),
        });
        await refresh();
      } catch (error) {
        alert(error.message);
      }
    });

    pinButton.addEventListener("click", async () => {
      try {
        const endpoint = note.pinned ? "unpin" : "pin";
        await request(`/api/notes/${note.id}/${endpoint}`, { method: "POST" });
        await refresh();
      } catch (error) {
        alert(error.message);
      }
    });

    archiveButton.addEventListener("click", async () => {
      try {
        const endpoint = note.archived ? "restore" : "archive";
        await request(`/api/notes/${note.id}/${endpoint}`, { method: "POST" });
        await refresh();
      } catch (error) {
        alert(error.message);
      }
    });

    deleteButton.addEventListener("click", async () => {
      if (!window.confirm(`Delete note #${note.id}?`)) {
        return;
      }
      try {
        await request(`/api/notes/${note.id}`, { method: "DELETE" });
        await refresh();
      } catch (error) {
        alert(error.message);
      }
    });

    notesList.appendChild(card);
  }
}

async function loadNotes() {
  const params = new URLSearchParams();
  params.set("all", String(state.showArchived));
  params.set("sort", state.sort);
  if (state.tag) {
    params.set("tag", state.tag);
  }

  if (state.query) {
    params.set("q", state.query);
    return request(`/api/search?${params.toString()}`);
  }
  return request(`/api/notes?${params.toString()}`);
}

async function loadStats() {
  return request("/api/stats");
}

async function refresh() {
  const [notes, stats] = await Promise.all([loadNotes(), loadStats()]);
  renderNotes(notes);
  renderStats(stats);
}

noteForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    text: document.getElementById("note-text").value,
    tags: parseTags(document.getElementById("note-tags").value),
    pinned: document.getElementById("note-pin").checked,
  };

  try {
    await request("/api/notes", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    noteForm.reset();
    await refresh();
  } catch (error) {
    alert(error.message);
  }
});

searchInput.addEventListener("input", async (event) => {
  state.query = event.target.value.trim();
  await refresh();
});

tagFilter.addEventListener("input", async (event) => {
  state.tag = event.target.value.trim();
  await refresh();
});

showArchived.addEventListener("change", async (event) => {
  state.showArchived = event.target.checked;
  await refresh();
});

sortSelect.addEventListener("change", async (event) => {
  state.sort = event.target.value;
  await refresh();
});

refresh().catch((error) => {
  renderEmptyState();
  statsPanel.innerHTML = `<p class="eyebrow">Status</p><p>${error.message}</p>`;
});
