const apiBase = window.location.origin;

async function checkBackend() {
  const el = document.getElementById("status-indicator");
  try {
    const res = await fetch(`${apiBase}/health`);
    if (!res.ok) throw new Error("health not ok");
    el.textContent = "Backend: online";
    el.classList.remove("error");
    el.classList.add("ok");
  } catch (e) {
    el.textContent = "Backend: unreachable";
    el.classList.remove("ok");
    el.classList.add("error");
  }
}

function getSelectedDomains() {
  const chips = document.querySelectorAll("#domain-search .obp-chip input[type=checkbox]");
  const domains = [];
  chips.forEach((c) => {
    if (c.checked) domains.push(c.value);
  });
  return domains;
}

function renderSearchResults(papers) {
  const container = document.getElementById("search-results");
  container.innerHTML = "";
  if (!papers || papers.length === 0) {
    const empty = document.createElement("p");
    empty.className = "obp-analysis-empty";
    empty.textContent = "No papers found for this query and filters.";
    container.appendChild(empty);
    return;
  }

  papers.forEach((p) => {
    const card = document.createElement("div");
    card.className = "obp-result-card";

    const title = document.createElement("h3");
    title.className = "obp-result-title";
    const link = document.createElement("a");
    link.href = p.url || "#";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = p.title || p.url || "Untitled";
    title.appendChild(link);

    const meta = document.createElement("div");
    meta.className = "obp-result-meta";
    const left = document.createElement("span");
    left.textContent = p.domain || "";
    const right = document.createElement("span");
    right.textContent = p.published_date || "";
    meta.appendChild(left);
    meta.appendChild(right);

    const footer = document.createElement("div");
    footer.className = "obp-card-footer";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "Analyze";
    btn.addEventListener("click", () => {
      const urlInput = document.getElementById("paper-url");
      if (p.url) urlInput.value = p.url;
      analyzePaper(p.url || "");
    });
    footer.appendChild(btn);

    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(footer);
    container.appendChild(card);
  });
}

function renderAnalysis(result) {
  const container = document.getElementById("analysis-content");
  container.classList.remove("obp-analysis-empty");
  container.innerHTML = "";

  const header = document.createElement("div");
  header.className = "obp-analysis-header";

  const title = document.createElement("h3");
  title.textContent = result.title || "Analyzed paper";
  header.appendChild(title);

  const idInfo = document.createElement("small");
  idInfo.textContent = `paper_id: ${result.paper_id}`;
  header.appendChild(idInfo);

  container.appendChild(header);

  if (result.links && result.links.length) {
    const linkRow = document.createElement("p");
    linkRow.className = "obp-section-help";
    const a = document.createElement("a");
    a.href = result.links[0];
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = result.links[0];
    linkRow.appendChild(document.createTextNode("Source: "));
    linkRow.appendChild(a);
    container.appendChild(linkRow);
  }

  if (result.summary) {
    const summarySection = document.createElement("div");
    summarySection.className = "obp-summary-section";
    
    const summaryLabel = document.createElement("h4");
    summaryLabel.textContent = "Paper Summary";
    summarySection.appendChild(summaryLabel);
    
    const summaryEl = document.createElement("p");
    summaryEl.className = "obp-summary";
    summaryEl.textContent = result.summary;
    summarySection.appendChild(summaryEl);
    
    container.appendChild(summarySection);
  }

  if (result.dataset_query) {
    const dqWrapper = document.createElement("div");
    dqWrapper.className = "obp-dataset-query";

    const dqLabel = document.createElement("div");
    dqLabel.className = "obp-dataset-query-label";
    dqLabel.innerHTML = "📊 <strong>Dataset Generation Query for Reproduction</strong>";

    const dqText = document.createElement("div");
    dqText.className = "obp-dataset-query-text";
    dqText.textContent = result.dataset_query;

    const dqCopy = document.createElement("button");
    dqCopy.type = "button";
    dqCopy.className = "obp-copy-btn";
    dqCopy.textContent = "Copy Query";
    dqCopy.addEventListener("click", () => {
      navigator.clipboard.writeText(result.dataset_query).then(() => {
        dqCopy.textContent = "Copied!";
        setTimeout(() => { dqCopy.textContent = "Copy Query"; }, 2000);
      });
    });

    dqWrapper.appendChild(dqLabel);
    dqWrapper.appendChild(dqText);
    dqWrapper.appendChild(dqCopy);
    container.appendChild(dqWrapper);
  }

  if (result.datasets && result.datasets.length) {
    const row = document.createElement("div");
    row.className = "obp-pill-row";
    const label = document.createElement("span");
    label.className = "obp-section-help";
    label.textContent = "Detected datasets:";
    row.appendChild(label);
    result.datasets.forEach((d) => {
      const pill = document.createElement("span");
      pill.className = "obp-pill";
      pill.textContent = d;
      row.appendChild(pill);
    });
    container.appendChild(row);
  }

  if (result.tasks && result.tasks.length) {
    const row = document.createElement("div");
    row.className = "obp-pill-row";
    const label = document.createElement("span");
    label.className = "obp-section-help";
    label.textContent = "Detected tasks:";
    row.appendChild(label);
    result.tasks.forEach((t) => {
      const pill = document.createElement("span");
      pill.className = "obp-pill";
      pill.textContent = t;
      row.appendChild(pill);
    });
    container.appendChild(row);
  }

  const claims = result.claims || [];
  if (claims.length) {
    const table = document.createElement("table");
    table.className = "obp-claims-table";

    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    ["Metric", "Dataset", "Task", "Reported", "Sentence"].forEach((h) => {
      const th = document.createElement("th");
      th.textContent = h;
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    claims.forEach((c) => {
      const tr = document.createElement("tr");

      const metricTd = document.createElement("td");
      metricTd.className = "metric-col";
      metricTd.textContent = c.metric || "";

      const datasetTd = document.createElement("td");
      datasetTd.textContent = c.dataset || "";

      const taskTd = document.createElement("td");
      taskTd.textContent = c.task || "";

      const reportedTd = document.createElement("td");
      reportedTd.textContent = c.reported != null ? String(c.reported) : "";

      const setupTd = document.createElement("td");
      setupTd.className = "setup-col";
      setupTd.textContent = c.setup || "";

      tr.appendChild(metricTd);
      tr.appendChild(datasetTd);
      tr.appendChild(taskTd);
      tr.appendChild(reportedTd);
      tr.appendChild(setupTd);
      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    container.appendChild(table);
  } else {
    const noClaims = document.createElement("p");
    noClaims.className = "obp-section-help";
    noClaims.textContent = "No metric-like claims were detected heuristically.";
    container.appendChild(noClaims);
  }
}

async function analyzePaper(url) {
  if (!url) return;
  const container = document.getElementById("analysis-content");
  container.classList.remove("obp-analysis-empty");
  container.textContent = "Analyzing paper...";

  try {
    const res = await fetch(`${apiBase}/tools/obp.paper.analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paper_url: url }),
    });
    if (!res.ok) {
      const msg = await res.text();
      throw new Error(msg || `HTTP ${res.status}`);
    }
    const data = await res.json();
    renderAnalysis(data);
  } catch (e) {
    container.textContent = `Error analyzing paper: ${e}`;
  }
}

async function handleSearchSubmit(evt) {
  evt.preventDefault();
  const q = document.getElementById("search-query").value.trim();
  if (!q) return;

  const timeRange = document.getElementById("search-time-range").value;
  const maxResults = parseInt(document.getElementById("search-max-results").value || "10", 10);
  const domains = getSelectedDomains();

  const body = {
    query: q,
    search_depth: "advanced",
    time_range: timeRange || null,
    include_domains: domains,
    max_results: maxResults,
    include_raw_content: true,
  };

  const container = document.getElementById("search-results");
  container.innerHTML = "Searching...";

  try {
    const res = await fetch(`${apiBase}/tools/obp.paper.search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const msg = await res.text();
      throw new Error(msg || `HTTP ${res.status}`);
    }
    const data = await res.json();
    renderSearchResults(data.papers || []);
  } catch (e) {
    container.textContent = `Error searching: ${e}`;
  }
}

async function handleAnalyzeSubmit(evt) {
  evt.preventDefault();
  const url = document.getElementById("paper-url").value.trim();
  if (!url) return;
  analyzePaper(url);
}

function init() {
  const searchForm = document.getElementById("search-form");
  const analyzeForm = document.getElementById("analyze-form");

  if (searchForm) searchForm.addEventListener("submit", handleSearchSubmit);
  if (analyzeForm) analyzeForm.addEventListener("submit", handleAnalyzeSubmit);

  checkBackend();
}

window.addEventListener("DOMContentLoaded", init);
