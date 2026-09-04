/* agent_orchestration.js — Milestone 4
   Drives the Agent Orchestration page: runs quick actions or free-text
   problems through /api/orchestrator/run and renders the structured result. */

(function () {
  const resultBox = document.getElementById("orchResult");
  const indicator = document.getElementById("analyzingIndicator");
  const runBtn = document.getElementById("runOrchBtn");
  const input = document.getElementById("problemInput");

  function renderResult(data) {
    const agentChips = data.agents_consulted
      .map((a) => `<span class="agent-chip done"><i class="fa-solid fa-circle-check"></i> ${a}</span>`)
      .join("");

    const agentOutputs = data.agent_outputs
      .map(
        (a) => `<div class="orch-agent-output"><b>${a.agent}</b><span class="confidence-pill">${a.confidence}% confidence</span><br>${a.summary}</div>`
      )
      .join("");

    const riskClass =
      { Critical: "badge-critical-risk", High: "badge-high", Medium: "badge-medium", Low: "badge-low" }[data.risk_level] || "badge-medium";

    resultBox.innerHTML = `
      <div class="glass orch-result-card" style="margin-top:18px;">
        <div class="orch-section">
          <h4>Problem</h4>
          <p>${data.problem || "(quick action)"}</p>
        </div>
        <div class="orch-section">
          <h4>Agents Consulted</h4>
          <div class="agent-flow">${agentChips}</div>
        </div>
        <div class="orch-section">
          <h4>Risk Level</h4>
          <span class="badge-label ${riskClass}">${data.risk_level}</span>
        </div>
        <div class="orch-section">
          <h4>Recommendation</h4>
          <p><b>${data.recommendation}</b></p>
        </div>
        <div class="orch-section">
          <h4>Reasoning</h4>
          <p>${data.reasoning}</p>
        </div>
        <div class="orch-section">
          <h4>Action</h4>
          <p>${data.action}</p>
        </div>
        <div class="orch-section">
          <h4>Agent Outputs</h4>
          ${agentOutputs}
        </div>
      </div>
    `;
  }

  async function runOrchestration(payload) {
    indicator.style.display = "flex";
    resultBox.innerHTML = "";
    runBtn.disabled = true;
    try {
      const res = await fetch("/api/orchestrator/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (json.success) {
        renderResult(json.data);
      } else {
        resultBox.innerHTML = `<div class="glass" style="padding:16px;margin-top:16px;color:#ef4444;">${json.error}</div>`;
      }
    } catch (e) {
      resultBox.innerHTML = `<div class="glass" style="padding:16px;margin-top:16px;color:#ef4444;">Request failed: ${e}</div>`;
    } finally {
      indicator.style.display = "none";
      runBtn.disabled = false;
    }
  }

  document.querySelectorAll(".quick-action-btn").forEach((btn) => {
    btn.addEventListener("click", () => runOrchestration({ quick_action: btn.dataset.action }));
  });

  runBtn.addEventListener("click", () => {
    const problem = input.value.trim();
    if (!problem) return;
    runOrchestration({ problem });
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runBtn.click();
  });
})();
