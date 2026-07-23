const API_BASE = "/loan/sessions";
const INVENTORY_API_BASE = "/inventory";

const SESSION_ACTIONS = {
    CREATED: {label: "Marquer prête", endpoint: "ready"},
    READY: {label: "Démarrer", endpoint: "start"},
    IN_PROGRESS: {label: "Compléter", endpoint: "complete"},
};

const CANCELLABLE_STATUSES = ["CREATED", "READY", "IN_PROGRESS"];

const ASSIGNMENT_ACTIONS = {
    CREATED: {label: "Préparer", endpoint: "prepare"},
    PREPARED: {label: "Distribuer", endpoint: "distribute"},
    DISTRIBUTED: {label: "Confirmer", endpoint: "confirm"},
    CONFIRMED: {label: "Marquer retournée", endpoint: "return"},
};

function statusBadgeClass(status) {
    return "badge status-" + status.toLowerCase();
}

function formatDate(iso) {
    return new Date(iso).toLocaleString("fr-FR");
}

async function apiGet(path) {
    const response = await fetch(path);

    if (!response.ok) {
        throw new Error(`Erreur ${response.status}`);
    }

    return response.json();
}

async function apiPost(path) {
    const response = await fetch(path, {method: "POST"});
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.detail || `Erreur ${response.status}`);
    }

    return data;
}

async function apiPut(path, body) {
    const response = await fetch(path, {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.detail || `Erreur ${response.status}`);
    }

    return data;
}

function showError(message) {
    const el = document.getElementById("error-message");

    if (!el) {
        return;
    }

    el.textContent = message;
    el.hidden = false;
}

function clearError() {
    const el = document.getElementById("error-message");

    if (!el) {
        return;
    }

    el.hidden = true;
}

async function renderSessionList() {
    const tbody = document.getElementById("sessions-body");
    const emptyMessage = document.getElementById("empty-message");

    clearError();

    let sessions;

    try {
        sessions = await apiGet(`${API_BASE}/`);
    } catch (err) {
        showError("Impossible de charger les sessions.");
        return;
    }

    tbody.innerHTML = "";

    if (sessions.length === 0) {
        emptyMessage.hidden = false;
        return;
    }

    emptyMessage.hidden = true;

    for (const session of sessions) {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>#${session.id}</td>
            <td><span class="${statusBadgeClass(session.status)}">${session.status}</span></td>
            <td>${session.assignments.length}</td>
            <td>${formatDate(session.created_at)}</td>
            <td><a href="session.html?id=${session.id}">Voir</a></td>
        `;

        tbody.appendChild(row);
    }
}

function getSessionIdFromUrl() {
    return new URLSearchParams(window.location.search).get("id");
}

async function renderSessionDetail() {
    const sessionId = getSessionIdFromUrl();

    if (!sessionId) {
        showError("Aucune session sélectionnée.");
        return;
    }

    clearError();

    let session;

    try {
        session = await apiGet(`${API_BASE}/${sessionId}`);
    } catch (err) {
        showError("Session introuvable.");
        return;
    }

    document.getElementById("session-title").textContent = `Session #${session.id}`;

    const statusEl = document.getElementById("session-status");
    statusEl.textContent = session.status;
    statusEl.className = statusBadgeClass(session.status);

    renderSessionActions(session);
    renderAssignments(session);
}

function renderSessionActions(session) {
    const container = document.getElementById("session-actions");
    container.innerHTML = "";

    const action = SESSION_ACTIONS[session.status];

    if (action) {
        const button = document.createElement("button");
        button.textContent = action.label;

        button.addEventListener("click", async () => {
            clearError();

            try {
                await apiPost(`${API_BASE}/${session.id}/${action.endpoint}`);
                await renderSessionDetail();
            } catch (err) {
                showError(err.message);
            }
        });

        container.appendChild(button);
    }

    if (CANCELLABLE_STATUSES.includes(session.status)) {
        const cancelButton = document.createElement("button");
        cancelButton.textContent = "Forcer l'arrêt";
        cancelButton.className = "btn-danger";

        cancelButton.addEventListener("click", async () => {
            const confirmed = window.confirm(
                "Forcer l'arrêt de cette session ? Toutes les cartes non retournées seront libérées de l'inventaire. Cette action est irréversible."
            );

            if (!confirmed) {
                return;
            }

            clearError();

            try {
                await apiPost(`${API_BASE}/${session.id}/cancel`);
                await renderSessionDetail();
            } catch (err) {
                showError(err.message);
            }
        });

        container.appendChild(cancelButton);
    }
}

function renderAssignments(session) {
    const tbody = document.getElementById("assignments-body");
    tbody.innerHTML = "";

    for (const assignment of session.assignments) {
        const row = document.createElement("tr");
        const action = ASSIGNMENT_ACTIONS[assignment.status];

        const actionCell = action
            ? `<button data-assignment-id="${assignment.id}" data-endpoint="${action.endpoint}">${action.label}</button>`
            : "—";

        const cardLabel = assignment.card_name || `Carte #${assignment.card_id}`;

        row.innerHTML = `
            <td>${assignment.player_name}</td>
            <td>${cardLabel}</td>
            <td>${assignment.quantity}</td>
            <td><span class="${statusBadgeClass(assignment.status)}">${assignment.status}</span></td>
            <td>${actionCell}</td>
        `;

        tbody.appendChild(row);
    }

    tbody.querySelectorAll("button[data-endpoint]").forEach((button) => {
        button.addEventListener("click", async () => {
            clearError();

            const assignmentId = button.dataset.assignmentId;
            const endpoint = button.dataset.endpoint;

            try {
                await apiPost(`${API_BASE}/assignments/${assignmentId}/${endpoint}`);
                await renderSessionDetail();
            } catch (err) {
                showError(err.message);
            }
        });
    });
}

async function renderInventory() {
    const tbody = document.getElementById("inventory-body");
    const emptyMessage = document.getElementById("empty-message");

    clearError();

    let items;

    try {
        items = await apiGet(`${INVENTORY_API_BASE}/`);
    } catch (err) {
        showError("Impossible de charger l'inventaire.");
        return;
    }

    tbody.innerHTML = "";

    if (items.length === 0) {
        emptyMessage.hidden = false;
        return;
    }

    emptyMessage.hidden = true;

    for (const item of items) {
        const row = document.createElement("tr");
        const cardLabel = item.card_name || `Carte #${item.card_id}`;

        row.innerHTML = `
            <td>${cardLabel}</td>
            <td>${item.quantity}</td>
            <td>${item.available_quantity}</td>
            <td>
                <input type="number" min="0" value="${item.quantity}" data-card-id="${item.card_id}" class="quantity-input"/>
                <button data-card-id="${item.card_id}" class="save-quantity-btn">Enregistrer</button>
            </td>
        `;

        tbody.appendChild(row);
    }

    tbody.querySelectorAll(".save-quantity-btn").forEach((button) => {
        button.addEventListener("click", async () => {
            clearError();

            const cardId = button.dataset.cardId;
            const input = tbody.querySelector(`.quantity-input[data-card-id="${cardId}"]`);
            const quantity = parseInt(input.value, 10);

            try {
                await apiPut(`${INVENTORY_API_BASE}/${cardId}`, {quantity});
                await renderInventory();
            } catch (err) {
                showError(err.message);
            }
        });
    });
}
