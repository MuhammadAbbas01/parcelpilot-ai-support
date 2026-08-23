async function load() {
  const role = document.getElementById("role").value;
  const content = document.getElementById("dashboardContent");
  const res = await fetch("/api/insights", {
    headers: { "X-User-Role": role, "X-User-Name": "demo-user" }
  });

  if (!res.ok) {
    document.getElementById("snapshot").textContent = "";
    content.innerHTML = '<div class="denied">Access denied (HTTP ' + res.status +
      ') — the "' + role + '" role does not have permission to view this dashboard. ' +
      'Only ops_manager or admin can access it.</div>';
    return;
  }

  const data = await res.json();
  document.getElementById("snapshot").textContent =
    "Dataset snapshot (reference \"now\"): " + data.dataset_snapshot;

  content.innerHTML = `
    <div class="card">
      <h2>SLA Risk — open tickets</h2>
      <p class="desc">Ranked by elapsed time vs. first-response target (breached first)</p>
      <table id="slaTable"><thead><tr><th>Ticket</th><th>Account</th><th>Subject</th><th>Severity</th><th>Elapsed / Target (hrs)</th><th>Status</th></tr></thead><tbody></tbody></table>
    </div>
    <div class="card">
      <h2>Issue Clusters</h2>
      <p class="desc">Open tickets grouped by shared topic — highlighted rows affect multiple customers</p>
      <table id="clusterTable"><thead><tr><th>Topic</th><th>Tickets</th><th>Accounts affected</th><th>Multi-customer?</th></tr></thead><tbody></tbody></table>
    </div>
    <div class="card">
      <h2>Order Anomalies</h2>
      <p class="desc">Carrier-fault orders with pickup still pending — surfaced before a complaint is filed</p>
      <table id="orderTable"><thead><tr><th>Order</th><th>Account</th><th>Carrier</th><th>Hours late</th><th>Status</th></tr></thead><tbody></tbody></table>
    </div>
  `;

  const slaBody = document.querySelector("#slaTable tbody");
  if (!data.sla_risk.length) {
    slaBody.innerHTML = '<tr><td colspan="6" class="empty">No open tickets.</td></tr>';
  }
  data.sla_risk.forEach(r => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${r.ticket_id}</td><td>${r.account_name}</td><td>${r.subject}</td>
      <td>${r.inferred_severity}</td><td>${r.elapsed_hours} / ${r.target_hours}</td>
      <td><span class="badge ${r.sla_status}">${r.sla_status.replace("_"," ")}</span></td>`;
    slaBody.appendChild(tr);
  });

  const clusterBody = document.querySelector("#clusterTable tbody");
  if (!data.clusters.length) {
    clusterBody.innerHTML = '<tr><td colspan="4" class="empty">No clusters detected.</td></tr>';
  }
  data.clusters.forEach(c => {
    const tr = document.createElement("tr");
    if (c.multi_customer) tr.className = "multi-row";
    tr.innerHTML = `<td>${c.topic.replace(/_/g," ")}</td><td>${c.ticket_ids.join(", ")}</td>
      <td>${c.accounts_affected.join(", ")}</td><td>${c.multi_customer ? "Yes" : "No"}</td>`;
    clusterBody.appendChild(tr);
  });

  const orderBody = document.querySelector("#orderTable tbody");
  if (!data.order_anomalies.length) {
    orderBody.innerHTML = '<tr><td colspan="5" class="empty">No anomalies detected.</td></tr>';
  }
  data.order_anomalies.forEach(o => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${o.order_id}</td><td>${o.account_name}</td><td>${o.carrier}</td>
      <td>${o.late_hours}</td><td>${o.status}</td>`;
    orderBody.appendChild(tr);
  });
}
load();
document.getElementById("role").addEventListener("change", load);
