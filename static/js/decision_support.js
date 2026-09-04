/* decision_support.js — Milestone 4
   Drives the Decision Support Center: sends a question or quick action to
   the backend and renders the structured analysis result. */

(function () {
  const resultBox = document.getElementById("decisionResult");
  const indicator = document.getElementById("analyzingIndicator");
  const askBtn = document.getElementById("askBtn");
  const input = document.getElementById("questionInput");

  function renderResult(data) {
    const agentChips = data.agents_consulted
      .map((a) => `<span class="agent-chip done"><i class="fa-solid fa-circle-check"></i> ${a}</span>`)
      .join("");

    const riskClass =
      { Critical: "badge-critical-risk", High: "badge-high", Medium: "badge-medium", Low: "badge-low" }[data.risk_level] || "badge-medium";

    resultBox.innerHTML = `
      <div class="glass orch-result-card" style="margin-top:18px;">
        <div class="orch-section"><h4>Question</h4><p>${data.problem}</p></div>
        <div class="orch-section"><h4>Agents Invoked</h4><div class="agent-flow">${agentChips}</div></div>
        <div class="orch-section"><h4>Analysis</h4>
          ${data.agent_outputs.map((a) => `<div class="orch-agent-output"><b>${a.agent}</b><span class="confidence-pill">${a.confidence}%</span><br>${a.summary}</div>`).join("")}
        </div>
        <div class="orch-section"><h4>Risk Level</h4><span class="badge-label ${riskClass}">${data.risk_level}</span></div>
        <div class="orch-section"><h4>Recommendation</h4><p><b>${data.recommendation}</b></p></div>
        <div class="orch-section"><h4>Reasoning</h4><p>${data.reasoning}</p></div>
        <div class="orch-section"><h4>Action</h4><p>${data.action}</p></div>
      </div>
    `;
  }

  async function ask(question) {
    indicator.style.display = "flex";
    resultBox.innerHTML = "";
    askBtn.disabled = true;
    try {
      const res = await fetch("/api/decision-support/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const json = await res.json();
      if (json.success) renderResult(json.data);
      else resultBox.innerHTML = `<div class="glass" style="padding:16px;margin-top:16px;color:#ef4444;">${json.error}</div>`;
    } catch (e) {
      resultBox.innerHTML = `<div class="glass" style="padding:16px;margin-top:16px;color:#ef4444;">Request failed: ${e}</div>`;
    } finally {
      indicator.style.display = "none";
      askBtn.disabled = false;
    }
  }

  async function runQuickAction(actionKey) {
    indicator.style.display = "flex";
    resultBox.innerHTML = "";
    try {
      const res = await fetch("/api/orchestrator/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quick_action: actionKey }),
      });
      const json = await res.json();
      if (json.success) renderResult(json.data);
      else resultBox.innerHTML = `<div class="glass" style="padding:16px;margin-top:16px;color:#ef4444;">${json.error}</div>`;
    } finally {
      indicator.style.display = "none";
    }
  }

  askBtn.addEventListener("click", () => {
    const q = input.value.trim();
    if (!q) return;
    ask(q);
  });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") askBtn.click(); });

  document.querySelectorAll(".sample-q-chip").forEach((chip) => {
    chip.addEventListener("click", () => { input.value = chip.dataset.q; ask(chip.dataset.q); });
  });

  document.querySelectorAll(".quick-action-btn").forEach((btn) => {
    btn.addEventListener("click", () => runQuickAction(btn.dataset.action));
  });
})();
