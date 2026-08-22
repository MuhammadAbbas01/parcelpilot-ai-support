# AI Tool Usage

Built this submission using Claude (Anthropic), via Claude's desktop
file/terminal access, for the full session: initial scaffolding,
switching the LLM provider from Anthropic to Groq and the model to
`openai/gpt-oss-120b` once free-tier constraints and a deprecated
model name came up, reading and integrating the real supplied data
pack (6 PDFs + xlsx) once it was downloaded, debugging a Groq SDK
version conflict and a datetime-serialization bug by running the
actual server and testing real requests against it, building the
proactive issue detection dashboard (Problem 1), and writing the
architecture/product notes. Every claim in this repo (tool traces,
SLA numbers, the Northstar/ORD-1001 example resolving correctly) was
verified by actually running the code, not just generated — see the
smoke-test output referenced in the architecture note.
