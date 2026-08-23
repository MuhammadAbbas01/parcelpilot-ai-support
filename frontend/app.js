const sessionId = crypto.randomUUID();
const log = document.getElementById("log");
const emptyState = document.getElementById("emptyState");
const inputBox = document.getElementById("inputBox");
const sendBtn = document.getElementById("sendBtn");

marked.setOptions({ breaks: true, gfm: true });

function renderMarkdown(text) {
  const raw = marked.parse(text || "");
  return DOMPurify.sanitize(raw);
}

function addUserMessage(text) {
  emptyState?.remove();
  const row = document.createElement("div");
  row.className = "row user";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  row.appendChild(bubble);
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
}

const TOOL_ICONS = {
  search_documents: "📄", search_deprecated_history: "🗄️",
  get_account: "🏢", get_order: "📦", get_tickets_for_account: "🎫",
  get_all_open_tickets: "🎫", calc_late_pickup_hours: "⏱️",
  calc_minutes_since_booking: "⏱️", get_dataset_snapshot_time: "🕒",
  propose_action: "✋", execute_action: "✅",
};

function friendlyToolLabel(tool, input) {
  const icon = TOOL_ICONS[tool] || "🔧";
  const args = Object.entries(input || {})
    .filter(([, v]) => v !== null && v !== undefined)
    .map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join(", ");
  return `${icon} ${tool}${args ? "(" + args + ")" : "()"}`;
}

function addToolTrace(trace) {
  if (!trace || !trace.length) return;
  const row = document.createElement("div");
  row.className = "row bot";
  const wrap = document.createElement("div");
  wrap.className = "tool-trace";
  trace.forEach(t => {
    const chip = document.createElement("div");
    chip.className = "tool-chip";
    chip.textContent = friendlyToolLabel(t.tool, t.input);
    wrap.appendChild(chip);
  });
  row.appendChild(wrap);
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
}

function addBotMessage(text) {
  const row = document.createElement("div");
  row.className = "row bot";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = renderMarkdown(text);
  row.appendChild(bubble);
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
}

function addThinking() {
  const row = document.createElement("div");
  row.className = "row bot";
  row.id = "thinkingRow";
  const div = document.createElement("div");
  div.className = "thinking";
  div.textContent = "Thinking…";
  row.appendChild(div);
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
  return row;
}

async function sendChatRequest(message, role, retriesLeft = 2) {
  try {
    return await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Role": role,
        "X-User-Name": "demo-user"
      },
      body: JSON.stringify({
        message, session_id: sessionId,
        user: { user_id: "demo-user", role, name: "Demo User" }
      })
    });
  } catch (err) {
    // Free tunnels occasionally drop a connection momentarily -- retry
    // silently before surfacing anything to the user.
    if (retriesLeft > 0) {
      await new Promise(r => setTimeout(r, 800));
      return sendChatRequest(message, role, retriesLeft - 1);
    }
    throw err;
  }
}

async function send() {
  const message = inputBox.value.trim();
  if (!message) return;
  addUserMessage(message);
  inputBox.value = "";
  sendBtn.disabled = true;
  inputBox.disabled = true;
  const thinkingRow = addThinking();

  try {
    const role = document.getElementById("role").value;
    const res = await sendChatRequest(message, role);
    thinkingRow.remove();

    if (!res.ok) {
      const errText = res.status === 403
        ? "Access denied — this role doesn't have permission for that."
        : `Request failed (HTTP ${res.status}).`;
      addBotMessage(errText);
      return;
    }
    const data = await res.json();
    addToolTrace(data.tool_trace || []);
    addBotMessage(data.reply || "");
  } catch (err) {
    thinkingRow.remove();
    addBotMessage("Connection hiccup — the tunnel dropped for a moment. **Please press Send again** (your message wasn't lost, just resend it).");
  } finally {
    sendBtn.disabled = false;
    inputBox.disabled = false;
    inputBox.focus();
  }
}

inputBox.addEventListener("keydown", e => {
  if (e.key === "Enter") send();
});
inputBox.focus();
