# Wayan Social Growth — The Agent-Powered Content Machine

How to grow Wayan's social media using the agents themselves: research goes in,
multi-channel content comes out, and everything reusable is remembered.

---

## 1. Positioning

**Wayan Onchain** = sharp, evidence-first onchain analysis that regular people
can act on — delivered by a creator who *builds his own AI agents in public*.
Two stories in one brand:

1. **The alpha:** token research, smart-money flows, scam detection (NFA framing).
2. **The build:** "I run Jupiter & Uran — here's how my agents made this post."

The second story is the differentiator: nobody else's research pipeline *is*
the content.

## 2. Target audience

- Crypto-curious retail who want signal without reading explorers themselves.
- Onchain analysts/degens who appreciate methodology (`onchain-alpha` skill).
- Builders/AI-curious followers drawn by the agent-workshop angle.
- Future workshop students (the beginner guide funnels here).

## 3. Content pillars

| Pillar | Share | Examples |
| --- | --- | --- |
| Onchain research & verdicts | 40% | token deep dives, smart-money moves, risk flags |
| Agent build-in-public | 25% | "Jupiter just transcribed and analyzed this video", new skills |
| Market events / reactions | 20% | emergency packages on big moves (workflow 5) |
| Education / glossary | 15% | "что такое LP lock", memory/agents explainers |

## 4. Channel strategy

| Channel | Role | Cadence | Format |
| --- | --- | --- | --- |
| **Telegram** | Home base — the CTA target of everything else | daily | alpha posts, verdicts, behind-the-scenes |
| **X** | Distribution + credibility | 1 post/day, 2 threads/week | threads from research, hot takes |
| **TikTok** | Top-of-funnel reach | 3–5/week | 45–60 s scripts from `content-engine` |
| **YouTube Shorts** | Search + longevity | 3/week | repurposed TikTok scripts, vertical |
| **Instagram Reels** | Same assets, different audience | 3/week | mirror TikTok with platform captions |
| **Threads** | Low-effort X mirror | repost days | trimmed thread openers |

Rule: **create once on research, publish six times.** Every piece ends with the
Telegram CTA.

## 5. From research to content — who does what

```
Research (Jupiter: onchain-alpha) 
   → Verdict + evidence (Markdown, transcripts/)
      → Content (Jupiter: content-engine — hook/script/caption per channel)
         → Review (you, в Telegram или Obsidian)
            → Publish (you) → Memory (OpenViking: what performed)
               → Reuse (Git: frameworks; weekly recall → calendar)
```

- **Jupiter** — does the heavy lifting: research, skill chaining
  (`file-analyst → onchain-alpha → content-engine`), voice/PDF/video→content,
  drafts in `outbox/` delivered back to Telegram.
- **Uran** — keeps the machine alive: service health, queue checks, OpenViking
  health, restarts; weekly ops report so the pipeline never silently dies.
- **OpenViking** — remembers brand voice, what performed, past verdicts, running
  narratives (`memory_recall "что заходило на этой неделе"` → calendar input).
- **Git** — versioned, reusable **frameworks**: the templates below live in the
  repo; hooks/structures that worked get committed and reused, not reinvented.
- **Obsidian** — your human window into the same Markdown: browse transcripts,
  edit drafts, link research notes into series.

## 6. The 8 workflows

### W1 — Onchain research → X thread
1. Telegram → Jupiter: «разбери токен X и сделай X-thread».
2. Chain: `onchain-alpha` (verdict + evidence) → `content-engine` (thread).
3. Output to `outbox/` → delivered as file → you review → post.
*Template: X thread (below).*

### W2 — Onchain research → Telegram post
Same research, alpha-post format: shorter, verdict-first, evidence bullets,
"not financial advice" footer. One research session feeds W1+W2 together.

### W3 — Voice note → Reels script
Record a 1-minute voice idea → Groq transcribes → `content-engine` returns
hook + 45–60 s script + caption + hashtags. Transcript saved to `transcripts/`
so the idea is never lost.

### W4 — PDF/report → content series
Upload report with caption «сделай контент-серию» → `file-analyst` extracts
key points → `content-engine` produces N posts (1 thread + 3 shorts scripts +
2 Telegram posts), each tied to one insight.

### W5 — Market event → emergency content package
Big move happens → one message: «срочный пакет по событию X» → Jupiter returns
within minutes: 1 Telegram alert post + 1 X hot-take + 1 short-script.
Speed is the value; templates keep quality.

### W6 — Weekly memory recall → content calendar
Weekly: «memory_recall: темы, верди́кты и реакции за неделю → предложи
контент-календарь на следующую». OpenViking surfaces what resonated; Jupiter
drafts a 7-day calendar; you approve; calendar saved to Markdown (Git).

### W7 — Long video/transcript → 5 short clips
Send video (≤20 MB) or a direct/YouTube link (yt-dlp optional) → audio
transcript **+ visual keyframe analysis** (with `VIDEO_VISUAL_ANALYSIS=true`,
ffmpeg extracts evenly-spaced frames that Claude inspects) → Jupiter splits
into 5 self-contained clip scripts with timestamps, hooks, and captions — and
can now reference what's *on screen* (scenes, charts, text overlays), not just
what's said. Frames are temporary and deleted after the reply.

### W8 — Community questions → FAQ/content ideas
Paste/export community questions → Jupiter clusters them → top-10 FAQ (Telegram
pinned post) + each cluster becomes a content idea in the calendar. Repeated
questions are stored to memory so answers stay consistent.

## 7. Templates (reusable frameworks — keep in Git, evolve via proposals)

### X post
```
{hook — 1 line, no preamble}
{insight in 1–2 lines, concrete number or onchain fact}
{verdict or implication}
🔗 Full breakdown in TG → {link}
```

### X thread
```
1/ {hook: tension or number} 
2/ {context: what the token/event is}
3–5/ {evidence: flows, holders, liquidity — one point per tweet}
6/ {risks — honest}
7/ {verdict: watch/avoid/deep dive + why}
8/ {CTA: deeper version in Telegram → link} 
```

### Telegram alpha post
```
⚡️ {TOKEN} — {one-line thesis}

Что вижу:
• {onchain fact 1}
• {onchain fact 2}
• {risk}

Вердикт: {watch / avoid / deep dive} — {1 строка почему}

NFA. Источники: {links}
```

### TikTok/Reels script (45–60 s)
```
HOOK (0–3 s): {scroll-stopper, говорит в камеру}
SETUP (3–10 s): {что случилось / что за токен}
MEAT (10–45 s): {3 конкретных факта, по одному на сцену}
PAYOFF (45–55 s): {вердикт / вывод}
CTA (55–60 s): «Полный разбор — в телеграме, ссылка в профиле»
CAPTION: {1 строка + 5–8 хэштегов}
```

### YouTube Shorts script
Same beats as Reels, plus: title ≤60 chars with the number/tension up front;
first line of description repeats the hook; end-screen line: «Подпишись —
каждый день разбор».

### CTA to Telegram (standard)
```
Полные разборы, вердикты и сигналы — в Telegram: {link}
```

### Weekly content report
```
# Week {N} — Content Report
Published: TG {n}, X {n}, TikTok {n}, Shorts {n}, Reels {n}, Threads {n}
Top performer: {post} — {metric, why it worked}
Flop: {post} — {hypothesis}
Memory updates: {what was stored}
Next week focus: {pillar/theme}
```

## 8. Operating rhythm

- **Daily (15 min):** 1 research prompt → W1+W2 outputs → review → publish.
- **3×/week:** one W3 voice note → short-form batch.
- **Weekly:** W6 calendar + weekly report; Uran ops report; commit reusable
  frameworks/templates that proved themselves.
- **On events:** W5 emergency package.

Quality bar: agents draft, **human publishes**. Nothing auto-posts — the same
no-autonomous-external-actions principle as the rest of the system.
