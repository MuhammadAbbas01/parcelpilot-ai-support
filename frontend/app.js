const sessionId = crypto.randomUUID();
const log = document.getElementById("log");

function addMsg(text, cls) {
  const div = document.createElement("div");
  div.className = "msg " + cls;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function addToolTrace(trace) {
  trace.forEach(t => {
    const div = document.createElement("div");
    div.className = "tool";
    div.textContent = `🔧 ${t.tool}(${JSON.stringify(t.input)})`;
    log.appendChild(div);
  });
}

async function send() {
  const box = document.getElementById("inputBox");
  const message = box.value.trim();
  if (!message) return;
  addMsg(message, "user");
  box.value = "";

  const role = document.getElementById("role").value;
  const res = await fetch("/api/chat", {
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
  const data = await res.json();
  addToolTrace(data.tool_trace || []);
  addMsg(data.reply, "bot");
}

document.getElementById("inputBox").addEventListener("keydown", e => {
  if (e.key === "Enter") send();
});
