const API_BASE = "/loan/sessions";
const INVENTORY_API_BASE = "/inventory";
const MTGO_API_BASE = "/mtgo";

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

async function apiPostJson(path, body) {
    const response = await fetch(path, {
        method: "POST",
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

    if (session.status === "IN_PROGRESS" && session.assignments.some((a) => a.status === "CREATED")) {
        const prepareAllButton = document.createElement("button");
        prepareAllButton.textContent = "Préparer tout";

        prepareAllButton.addEventListener("click", async () => {
            clearError();

            try {
                await apiPost(`${API_BASE}/${session.id}/prepare-all`);
                await renderSessionDetail();
            } catch (err) {
                showError(err.message);
            }
        });

        container.appendChild(prepareAllButton);
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

let mtgoJobsPollHandle = null;
let selectedMtgoJobId = null;

function jobStatusBadgeClass(status) {
    return "badge status-" + status.toLowerCase();
}

async function renderMtgoAdmin() {
    document.getElementById("give-btn").addEventListener("click", async () => {
        clearError();
        const sessionId = document.getElementById("give-session-id").value;

        if (!sessionId) {
            showError("ID de session requis.");
            return;
        }

        try {
            const job = await apiPost(`${MTGO_API_BASE}/sessions/${sessionId}/give`);
            selectedMtgoJobId = job.id;
            await renderJobsTable();
            await renderJobDetail(job.id);
        } catch (err) {
            showError(err.message);
        }
    });

    document.getElementById("return-btn").addEventListener("click", async () => {
        clearError();
        const sessionId = document.getElementById("return-session-id").value;
        const mtgoUsername = document.getElementById("return-mtgo-username").value;

        if (!sessionId || !mtgoUsername) {
            showError("ID de session et pseudo MTGO requis.");
            return;
        }

        try {
            const job = await apiPostJson(`${MTGO_API_BASE}/sessions/${sessionId}/return`, {
                mtgo_username: mtgoUsername,
            });
            selectedMtgoJobId = job.id;
            await renderJobsTable();
            await renderJobDetail(job.id);
        } catch (err) {
            showError(err.message);
        }
    });

    document.getElementById("integrity-check-btn").addEventListener("click", async () => {
        clearError();

        try {
            const job = await apiPost(`${MTGO_API_BASE}/integrity-check`);
            selectedMtgoJobId = job.id;
            await renderJobsTable();
            await renderJobDetail(job.id);
        } catch (err) {
            showError(err.message);
        }
    });

    await renderJobsTable();

    if (mtgoJobsPollHandle) {
        clearInterval(mtgoJobsPollHandle);
    }

    mtgoJobsPollHandle = setInterval(async () => {
        await renderJobsTable();

        if (selectedMtgoJobId) {
            await renderJobDetail(selectedMtgoJobId);
        }
    }, 5000);
}

async function renderJobsTable() {
    const tbody = document.getElementById("mtgo-jobs-body");
    const emptyMessage = document.getElementById("empty-message");

    if (!tbody) {
        return;
    }

    let jobs;

    try {
        jobs = await apiGet(`${MTGO_API_BASE}/jobs/`);
    } catch (err) {
        showError("Impossible de charger les jobs MTGO.");
        return;
    }

    tbody.innerHTML = "";

    if (jobs.length === 0) {
        emptyMessage.hidden = false;
        return;
    }

    emptyMessage.hidden = true;

    for (const job of jobs) {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>#${job.id}</td>
            <td>${job.job_type}</td>
            <td><span class="${jobStatusBadgeClass(job.status)}">${job.status}</span></td>
            <td>${job.session_id ?? "—"}</td>
            <td>${job.mtgo_username ?? "—"}</td>
            <td>${formatDate(job.created_at)}</td>
            <td><button data-job-id="${job.id}" class="detail-job-btn">Détails</button></td>
        `;

        tbody.appendChild(row);
    }

    tbody.querySelectorAll(".detail-job-btn").forEach((button) => {
        button.addEventListener("click", () => {
            selectedMtgoJobId = parseInt(button.dataset.jobId, 10);
            renderJobDetail(selectedMtgoJobId);
        });
    });
}

function renderReconciliationSection(reconciliation, job) {
    const stillOwed = reconciliation.still_owed || {};
    const toGiveBack = reconciliation.to_give_back || {};

    if (Object.keys(stillOwed).length === 0 && Object.keys(toGiveBack).length === 0) {
        return "<p>Aucun écart — tout est revenu comme prévu.</p>";
    }

    let html = "";

    if (Object.keys(stillOwed).length > 0) {
        html += "<h4>Encore dû</h4><ul>";
        for (const [name, qty] of Object.entries(stillOwed)) {
            html += `<li>${name} × ${qty}</li>`;
        }
        html += "</ul>";
        html += `<button class="retry-job-btn" data-job-id="${job.id}">Relancer la récupération</button>`;
    }

    if (Object.keys(toGiveBack).length > 0) {
        html += "<h4>Excédent reçu à rendre</h4><ul>";
        for (const [name, qty] of Object.entries(toGiveBack)) {
            html += `<li>${name} × ${qty}</li>`;
        }
        html += "</ul>";
        html += `<button class="give-back-btn btn-danger" data-job-id="${job.id}" `
            + `data-mtgo-username="${job.mtgo_username}" `
            + `data-cards='${JSON.stringify(toGiveBack)}'>Rendre l'excédent</button>`;
    }

    return html;
}

function renderIntegritySection(result) {
    const missing = result.missing || {};
    const extra = result.extra || {};

    if (Object.keys(missing).length === 0 && Object.keys(extra).length === 0) {
        return "<p>Intégrité du cube OK — aucun écart avec la référence.</p>";
    }

    let html = "";

    if (Object.keys(missing).length > 0) {
        html += "<h4>Manquant</h4><ul>";
        for (const [name, qty] of Object.entries(missing)) {
            html += `<li>${name} × ${qty}</li>`;
        }
        html += "</ul>";
    }

    if (Object.keys(extra).length > 0) {
        html += "<h4>En trop</h4><ul>";
        for (const [name, qty] of Object.entries(extra)) {
            html += `<li>${name} × ${qty}</li>`;
        }
        html += "</ul>";
    }

    return html;
}

function wireCorrectiveActionButtons(container) {
    const retryBtn = container.querySelector(".retry-job-btn");

    if (retryBtn) {
        retryBtn.addEventListener("click", async () => {
            clearError();

            try {
                const newJob = await apiPost(`${MTGO_API_BASE}/jobs/${retryBtn.dataset.jobId}/retry`);
                selectedMtgoJobId = newJob.id;
                await renderJobsTable();
                await renderJobDetail(newJob.id);
            } catch (err) {
                showError(err.message);
            }
        });
    }

    const giveBackBtn = container.querySelector(".give-back-btn");

    if (giveBackBtn) {
        giveBackBtn.addEventListener("click", async () => {
            const confirmed = window.confirm(
                "Rendre l'excédent de cartes au joueur ? Cette action crée un binder réel côté bot."
            );

            if (!confirmed) {
                return;
            }

            clearError();

            try {
                const cards = JSON.parse(giveBackBtn.dataset.cards);
                const newJob = await apiPostJson(`${MTGO_API_BASE}/give-back`, {
                    mtgo_username: giveBackBtn.dataset.mtgoUsername,
                    cards: cards,
                    retry_of_job_id: parseInt(giveBackBtn.dataset.jobId, 10),
                });
                selectedMtgoJobId = newJob.id;
                await renderJobsTable();
                await renderJobDetail(newJob.id);
            } catch (err) {
                showError(err.message);
            }
        });
    }
}

async function renderJobDetail(jobId) {
    const container = document.getElementById("mtgo-job-detail");

    if (!container) {
        return;
    }

    let job;

    try {
        job = await apiGet(`${MTGO_API_BASE}/jobs/${jobId}`);
    } catch (err) {
        showError("Job introuvable.");
        return;
    }

    let html = `<h3>Job #${job.id} (${job.job_type}) — `
        + `<span class="${jobStatusBadgeClass(job.status)}">${job.status}</span></h3>`;

    if (job.error_message) {
        html += `<p class="error">${job.error_message}</p>`;
    }

    if (job.log_output) {
        html += `<pre class="job-log">${job.log_output}</pre>`;
    }

    if (job.result && job.result.reconciliation) {
        html += renderReconciliationSection(job.result.reconciliation, job);
    }

    if (job.job_type === "INTEGRITY_CHECK" && job.result) {
        html += renderIntegritySection(job.result);
    }

    container.innerHTML = html;
    wireCorrectiveActionButtons(container);
}
