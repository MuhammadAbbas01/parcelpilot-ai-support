async function load() {
  const res = await fetch("/api/insights", {
    headers: { "X-User-Role": "ops_manager", "X-User-Name": "demo-user" }
  });
  if (!res.ok) {
    document.getElementById("snapshot").textContent =
      "Access denied — this view requires ops_manager or admin role.";
    return;
  }
  const data = await res.json();
  document.getElementById("snapshot").textContent =
    "Dataset snapshot (reference 'now'): " + data.dataset_snapshot;

  const slaBody = document.querySelector("#slaTable tbody");
  data.sla_risk.forEach(r => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${r.ticket_id}</td><td>${r.account_name}</td><td>${r.subject}</td>
      <td>${r.inferred_severity}</td><td>${r.elapsed_hours} / ${r.target_hours}</td>
      <td class="${r.sla_status}">${r.sla_status.replace("_"," ")}</td>`;
    slaBody.appendChild(tr);
  });

  const clusterBody = document.querySelector("#clusterTable tbody");
  data.clusters.forEach(c => {
    const tr = document.createElement("tr");
    if (c.multi_customer) tr.className = "multi";
    tr.innerHTML = `<td>${c.topic.replace(/_/g," ")}</td><td>${c.ticket_ids.join(", ")}</td>
      <td>${c.accounts_affected.join(", ")}</td><td>${c.multi_customer ? "YES" : "no"}</td>`;
    clusterBody.appendChild(tr);
  });

  const orderBody = document.querySelector("#orderTable tbody");
  data.order_anomalies.forEach(o => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${o.order_id}</td><td>${o.account_name}</td><td>${o.carrier}</td>
      <td>${o.late_hours}</td><td>${o.status}</td>`;
    orderBody.appendChild(tr);
  });
}
load();
