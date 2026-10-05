// The frontend talks to the API through the same origin (/api), routed by Nginx or the Ingress.
const API = "/api";
const STATUSES = ["Applied", "Interview", "Offer", "Rejected"];
let filter = "";

const $ = (sel) => document.querySelector(sel);

async function request(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.status === 204 ? null : res.json();
}

function el(tag, text, cls) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (cls) e.className = cls;
  return e;
}

async function loadStats() {
  const s = await request("/stats");
  $("#s-total").textContent = s.total;
  $("#s-interview").textContent = s.by_status.Interview;
  $("#s-offer").textContent = s.by_status.Offer;
  $("#s-response").textContent = s.response_rate + "%";
}

async function loadJobs() {
  const jobs = await request("/jobs" + (filter ? `?status_filter=${filter}` : ""));
  const body = $("#jobs");
  body.replaceChildren();
  $("#empty").hidden = jobs.length > 0;

  for (const job of jobs) {
    const tr = document.createElement("tr");
    tr.append(el("td", job.company), el("td", job.title), el("td", job.source), el("td", job.applied_on));

    const select = document.createElement("select");
    select.className = "status " + job.status.toLowerCase();
    for (const s of STATUSES) {
      const opt = el("option", s);
      opt.selected = s === job.status;
      select.append(opt);
    }
    select.onchange = async () => {
      await request(`/jobs/${job.id}`, { method: "PATCH", body: JSON.stringify({ status: select.value }) });
      refresh();
    };
    const statusTd = document.createElement("td");
    statusTd.append(select);

    const del = el("button", "✕", "delete");
    del.title = "Delete";
    del.onclick = async () => {
      await request(`/jobs/${job.id}`, { method: "DELETE" });
      refresh();
    };
    const delTd = document.createElement("td");
    delTd.append(del);

    tr.append(statusTd, delTd);
    body.append(tr);
  }
}

function refresh() {
  loadJobs().catch(console.error);
  loadStats().catch(console.error);
}

$("#add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  if (!data.applied_on) delete data.applied_on;
  await request("/jobs", { method: "POST", body: JSON.stringify(data) });
  e.target.reset();
  refresh();
});

document.querySelectorAll(".filters button").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll(".filters button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    filter = btn.dataset.filter;
    loadJobs().catch(console.error);
  };
});

fetch("/healthz").then((r) => r.json()).then((h) => ($("#version").textContent = h.version)).catch(() => {});
refresh();
