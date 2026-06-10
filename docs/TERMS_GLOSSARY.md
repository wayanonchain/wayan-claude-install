# Terms Glossary (plain English)

New to this? Here are the words that show up in the docs, explained simply.

| Term | In one sentence |
| --- | --- |
| **SSH** | A secure way to log in to and control another computer over the internet from your terminal (`ssh root@SERVER_IP`). |
| **VPS** | "Virtual Private Server" — a small Linux computer you rent in the cloud that runs 24/7; this is where the agents live. |
| **Git** | A tool that tracks changes to files (versions/history) so you can review and roll back. |
| **GitHub** | A website that hosts Git repositories online (where this project's code and your fork live). |
| **Repo / Repository** | A folder of project files tracked by Git. |
| **Docker** | Software that runs apps in isolated "containers"; here it runs OpenViking. |
| **Docker Compose** | A way to define and start Docker containers from a `docker-compose.yml` file. |
| **systemd** | Linux's service manager; it keeps the agents (`wayan-jupiter`, `wayan-uran`) running and restarts them if they crash. |
| **Service / daemon** | A program that runs in the background continuously (like the Telegram gateways). |
| **env file** | A plain text file of `KEY=value` settings (e.g. `/etc/wayan-jupiter.env`) that holds configuration and secrets like tokens. |
| **API key** | A secret password-like string that lets your code use a paid service (Groq, OpenAI); never share or commit it. |
| **Token** | Similar to an API key — e.g. a Telegram **bot token** that lets the gateway control your bot. |
| **Markdown** | A simple text format for notes/docs (the `.md` files); it's the project's long-term "source of truth." |
| **Obsidian** | A free app for reading/editing Markdown notes nicely (optional). |
| **Claude Code** | Anthropic's coding agent (`claude`); the "brain" each Wayan agent uses to think and act. |
| **MCP** | "Model Context Protocol" — how Claude Code plugins expose tools (e.g. the OpenViking memory tools). |
| **Plugin** | An add-on for Claude Code; here, the OpenViking memory plugin adds `memory_store`/`memory_recall`. |
| **OpenViking** | The service that gives the agents long-term **semantic memory** (runs in Docker on the VPS, localhost-only). |
| **Semantic memory** | Memory you search by *meaning* ("find what I said about the owner") rather than exact keywords; powered by embeddings. |
| **Embedding** | A numeric representation of text that lets a computer measure how similar two pieces of text are in meaning. |
| **Tenant (account/user)** | OpenViking's way of scoping memory to an owner (here `account=wayan`, `user=taras`). |
| **Transcript** | The Markdown file created from a voice note (Groq transcription) or an uploaded file's analysis. |
| **Skill** | A read-only `SKILL.md` playbook the agent follows for a specific kind of task. |
| **Gateway** | The small Python program that bridges Telegram messages to Claude Code. |
| **Headless** | Running a program with no interactive screen/prompt (`claude -p`); the agents run headless. |
| **Allow / Ask / Deny** | Permission rules: *allow* runs silently, *ask* prompts (and is blocked when headless), *deny* always blocks. |
| **Localhost / 127.0.0.1** | "This same machine only" — services bound here can't be reached from the internet. |

See also: [`MAC_SETUP.md`](MAC_SETUP.md), [`COSTS_AND_SERVICES.md`](COSTS_AND_SERVICES.md),
[`PUBLIC_TEMPLATE_GUIDE.md`](PUBLIC_TEMPLATE_GUIDE.md).
