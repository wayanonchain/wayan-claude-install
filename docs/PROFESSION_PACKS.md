# Profession Packs — Adapting Wayan Agents to Your Work

Wayan Agents is a general two-agent framework (research/content agent +
operations agent). A **profession pack** is a curated set of skills, memory
seeds, rules, and mapping entries that turns the same infrastructure into a
specialist assistant for a given profession.

**How a pack maps onto the framework:**

| Pack element | Lives in |
| --- | --- |
| Skills (playbooks) | `skills/<name>/SKILL.md` + routing line in `CLAUDE.md` |
| Durable knowledge | `orchestration/memory/cold.md` + OpenViking seeds |
| Hard rules | `orchestration/rules/` |
| Accounts/tools map | `orchestration/mapping/` |
| Agent identity | `templates/*/CLAUDE.md` |

All packs inherit the base safety model: no self-editing, proposals-only
improvement, minimal storage, secrets never in git, localhost-only memory.

---

## 1. Crypto / Onchain Analyst *(the original Wayan pack — included)*

- **Target user:** trader, analyst, alpha-channel owner.
- **Agent roles:** Jupiter = research + content from research; Uran = ops + data-pipeline health.
- **Skills:** `onchain-alpha` (tokens, smart money, flows, risk), `security-check`
  (scams, contracts, links), `content-engine` (turn research into posts).
- **Memory/rules:** watchlist + thesis history in memory; "never invent numbers,
  cite onchain evidence" rule; verdict format (`watch/avoid/deep dive`).
- **Example tasks:** "разбери токен X", "кто из smart money заходил за неделю",
  "сделай X-thread из этого разбора", PDF tokenomics review.
- **External services:** explorers/DEX APIs (Dexscreener, Solscan, Etherscan —
  explicitly configured), Telegram, Groq.
- **Risks:** financial-advice liability (always NFA framing), scam links,
  stale data presented as current.
- **Monetization:** paid alpha channel, research subscriptions, sponsored deep dives.

## 2. Content Creator / Influencer

- **Target user:** solo creator running TikTok/Reels/X/YouTube.
- **Agent roles:** Jupiter = scriptwriter + repurposer; Uran = publishing-pipeline ops.
- **Skills:** `content-engine` (hooks, scripts, captions), new `repurposer`
  (1 long video → N clips/posts), new `content-calendar`.
- **Memory/rules:** **brand voice** in `cold.md` (tone, banned phrases, CTA);
  what performed well (learnings → memory); posting cadence rules.
- **Example tasks:** voice note of an idea → Reels script; "перепакуй это видео
  в 5 коротких"; weekly content calendar from memory recall.
- **External services:** Groq (voice/video transcripts), platform analytics (manual export).
- **Risks:** platform ToS on automation, voice drift from the brand, copyright in sources.
- **Monetization:** more output per hour, productized "content OS" for other creators.

## 3. Founder / Startup Operator

- **Target user:** early-stage founder doing everything at once.
- **Agent roles:** Jupiter = analyst/writer (memos, decks, research);
  Uran = ops assistant (infra, checklists, reminders).
- **Skills:** new `investor-memo`, new `market-research`, `file-analyst`
  (customer interview transcripts, contracts).
- **Memory/rules:** company facts, ICP, metrics history in memory; "никогда не
  отправлять инвесторам без approve" rule.
- **Example tasks:** call recording → structured interview notes; "собери
  one-pager по конкурентам"; pitch-deck narrative draft; weekly ops digest.
- **External services:** Groq (call transcripts), GitHub (docs versioning).
- **Risks:** confidential data hygiene (minimal-storage helps), hallucinated
  market numbers — require sources.
- **Monetization:** time saved; packaged as "founder copilot" service.

## 4. Developer / DevOps

- **Target user:** solo dev or small team running services.
- **Agent roles:** Jupiter = code/research/PR summaries; Uran = first-line SRE
  (health, logs, restarts within its permission profile).
- **Skills:** `server-ops` (included), new `incident-report`, new `ci-watch`
  (parse CI logs → diagnosis).
- **Memory/rules:** services map (already in `mapping/`), runbooks in skills,
  postmortems in learnings; strict allow-list of restartable services.
- **Example tasks:** "почему упал сервис X" (logs→diagnosis→restart proposal),
  PR description from diff, weekly infra report.
- **External services:** GitHub/`gh`, CI provider.
- **Risks:** destructive ops — mitigated by the role permission profiles
  (stop/disable/down all gated); secrets in logs.
- **Monetization:** managed-ops retainer; internal toolchain.

## 5. Researcher / Student

- **Target user:** grad student, analyst, lifelong learner.
- **Agent roles:** Jupiter = reading/summarizing/organizing; Uran = library ops
  (vault structure, backups).
- **Skills:** `file-analyst` (included), new `citation-keeper` (sources +
  quotes with page refs), new `lecture-notes` (audio → structured notes).
- **Memory/rules:** topic map in memory; "always keep source + page for every
  claim" rule; Obsidian vault conventions in mapping.
- **Example tasks:** PDF → summary + key points + open questions; lecture voice
  recording → Markdown notes; "что я уже знаю про X" (memory recall).
- **External services:** Groq, Obsidian (local), OpenAI (memory).
- **Risks:** citation accuracy, paywalled-content handling, plagiarism norms.
- **Monetization:** personal productivity; tutoring/summary services.

## 6. Coach / Consultant

- **Target user:** 1-on-1 coach, consultant, therapist-adjacent professional.
- **Agent roles:** Jupiter = session prep + summaries + plans; Uran = practice ops.
- **Skills:** new `session-summary` (transcript → summary + actions),
  new `client-memory` (per-client recall conventions), `file-analyst`.
- **Memory/rules:** per-client context in OpenViking (one tenant *user* per
  client is a natural fit); **strict confidentiality rules** — no client data
  in git, transcripts pruned per retention policy.
- **Example tasks:** voice debrief after a session → summary + follow-ups;
  "что мы обсуждали с клиентом N в прошлый раз"; action-plan drafts.
- **External services:** Groq (session audio), calendar (manual).
- **Risks:** **privacy is the product** — client consent, data retention,
  regulatory rules (GDPR-like); never auto-store without approval.
- **Monetization:** more clients per week; premium "always-prepared" positioning.

## 7. Real Estate / Relocation Assistant

- **Target user:** relocation consultant, realtor, expat-services provider.
- **Agent roles:** Jupiter = research + client docs; Uran = checklist ops.
- **Skills:** new `location-research` (areas, prices, schools, visas),
  new `client-onboarding` (checklists, document lists), `file-analyst`
  (contracts, lease agreements).
- **Memory/rules:** local-knowledge base (verified facts only, dated); client
  preferences; "always date location facts — prices/rules change" rule.
- **Example tasks:** "сравни районы X и Y для семьи с детьми"; lease PDF →
  risks + questions; onboarding checklist for a new client; local guide drafts.
- **External services:** maps/listing portals (manual links), Groq.
- **Risks:** stale prices/regulations, legal advice boundaries (point to lawyers).
- **Monetization:** per-client packages, productized local guides.

## 8. SMM / Community Manager

- **Target user:** community manager running Telegram/X/YouTube for a brand.
- **Agent roles:** Jupiter = posts/threads/shorts + comment analysis;
  Uran = posting-pipeline + report ops.
- **Skills:** `content-engine` (included), new `community-pulse` (comment/
  question clustering → FAQ + content ideas), new `weekly-report`.
- **Memory/rules:** brand voice + community norms in memory; escalation rules
  ("toxic thread → flag to human, не отвечать"); content pillars in `cold.md`.
- **Example tasks:** "сделай Telegram-пост из этого анонса"; comments dump →
  top-10 questions → FAQ; weekly engagement report; X-thread from a blog post.
- **External services:** platform exports, Groq.
- **Risks:** brand-voice violations, replying to bait, platform automation ToS.
- **Monetization:** agency retainers, multi-community management at scale.

---

## How to build a new pack (recipe)

1. **Fork** the repo ([PUBLIC_TEMPLATE_GUIDE.md](PUBLIC_TEMPLATE_GUIDE.md)).
2. **Write 2–4 skills** — copy an existing `SKILL.md` as a shape: purpose, when
   to use, how to think, output format, rules.
3. **Add routing lines** to `templates/*/CLAUDE.md` `## Skills Usage`.
4. **Seed memory:** fill `orchestration/memory/cold.md`; store durable facts in
   OpenViking after install.
5. **Add rules** for your domain's red lines (`orchestration/rules/`).
6. **Map your tools** in `orchestration/mapping/` (no secrets).
7. Deploy with `install.sh` / `apply-templates.sh`; iterate via the learnings →
   proposal → approve loop.

Packs are **modular**: they change Markdown and skills only — the gateway,
queue, storage policy, permissions, and memory infrastructure are shared.
