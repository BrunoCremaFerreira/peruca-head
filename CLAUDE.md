# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code
in this repository.

## What this project is

`peruca-head` is the **voice device / client** ("the head") for the Peruca
assistant — think of it as a self-hosted Echo Dot. It does **not** contain the
assistant's intelligence. The brain already exists: the sibling project `../peruca`
exposes a REST API (`POST /llm/chat`, port 8000) that takes a natural-language
message and returns a reply.

The head's only job is to close the **voice loop** around that API:

```
[wake word / push-to-talk]
   → audio capture (VAD: record until silence)
       → STT, local (faster-whisper, pt-BR) ........ audio → text
           → POST /llm/chat (peruca) ................ text → reply
               → TTS, local (Piper, pt-BR) .......... reply → audio
                   → play on speaker
                       → back to IDLE
```

### Fixed product decisions
- **Target:** develop and validate everything on the **PC/laptop first** (the
  computer's own mic and speaker). Porting to a Raspberry Pi is a later phase
  (see Phase 6) and is intentionally out of scope until the PC loop is solid.
- **STT/TTS:** **100% local**, no cloud. This matches Peruca's self-hosted
  philosophy. CPU-only must work; GPU only accelerates Whisper.
- **Language:** **pt-BR** across the whole chain (STT, TTS, and eventually the
  wake word).

## The peruca API contract (already exists — do not reimplement)

```
POST http://localhost:8000/llm/chat
  body:  { "message": str, "external_user_id": str, "chat_id": str }
  reply: { "response": str, "external_user_id": str, "chat_id": str }

GET  /health → { "status": "ok" }
```

- `external_user_id` identifies the user; Peruca keeps **per-user persistent
  memory**, so this must be stable for a given device/user.
- `chat_id` keeps a conversation thread together.
- The head generates and persists both IDs locally (config/state). For now treat
  the device as single-user with a fixed `external_user_id`; multi-user-by-voice
  is a future epic, not a current goal.

When in doubt about request/response shapes, read the source of truth:
`../peruca/src/application/appservices/view_models.py` (`ChatRequest`,
`ChatResponse`) and `../peruca/src/.../routes.py`.

## Specialized agents (`.claude/agents/`)

| Agent | Role | When |
|---|---|---|
| `cientista` | ML / LLM / STT / TTS specialist (advisory only) | Any plan or change touching models, STT, TTS, VAD, audio pre/post-processing, wake word, latency, transcription/speech quality, or the text exchanged with peruca |
| `arquiteto` | Software architect (advisory only) | Design decisions, component boundaries, layering, coupling, pattern choice |
| `programador-tester` | Test author (TDD) | Writes the failing test before any implementation |
| `programador` | Implementer (TDD) | Implements the minimum to pass an existing test, then refactors |

### Mandatory validation by `cientista`

**Every plan and every change that affects the voice experience (models, STT, TTS,
VAD, audio handling, wake word, latency, or the text exchanged with peruca) must be
validated by the `cientista` agent before implementation, and the result must be
validated by it again before the work is considered complete.** The `cientista` is
consultative — it does not write code — but its approval, justified by an explicit
quality × latency × resource trade-off and a defined metric, is a prerequisite.

Recommended consultation order for ML/audio features:
`cientista` (approach + metrics) → `arquiteto` (fit + boundaries) →
`programador-tester` (failing tests) → `programador` (implementation) →
`cientista` (validate results against the metrics).

## TDD is mandatory — no exceptions

**Test-Driven Development MUST ALWAYS be used. Nothing may be implemented before its
tests are written first** — this applies equally to new features, changes to existing
behavior, and bug fixes. There is no exception.

The cycle is strictly:

```
1. RED      → Write the test first; confirm it FAILS (the behavior does not exist yet)
2. GREEN    → Implement the minimum needed to make the test pass
3. REFACTOR → Improve the code while keeping every test green
```

- **New feature:** write the failing test for the behavior, then implement.
- **Change:** update/add the test to express the new behavior (it must fail), then
  change the code.
- **Bug fix:** first write a test that reproduces the bug (it must fail), then fix the
  code so the test passes — this guards against regression.

Any code change submitted without a test written beforehand is considered incomplete
and must not be merged. The `programador-tester` agent writes the failing test; the
`programador` agent implements only after that test exists.

## Engineering conventions (shared with peruca)

These mirror `../peruca/CLAUDE.md` and apply here without exception:

- **All code in English** — identifiers, comments, docstrings, commit messages,
  docs. (User-facing voice text is pt-BR; that is data/config, not code.)
- **TDD is mandatory** — see the dedicated section above.
- **Never create a git commit automatically.** Commit only when the user explicitly
  asks.
- Keep external dependencies (audio devices, STT/TTS models, the peruca HTTP API)
  **behind thin wrappers** so they can be mocked in unit tests. No test may require
  a real microphone, speaker, model download, or a running peruca instance.

## Proposed stack

| Concern | Library | Notes |
|---|---|---|
| Audio I/O | `sounddevice` (PortAudio) | PCM capture and playback |
| Voice activity (VAD) | `silero-vad` (or `webrtcvad`) | record until silence |
| STT | `faster-whisper` (CTranslate2) | model `small`/`medium`, `language="pt"` |
| HTTP | `httpx` | calls `/llm/chat` |
| TTS | `piper-tts` | pt-BR voice (e.g. `pt_BR-faber-medium`) |
| Config | `pydantic-settings` + `.env` | API URL, IDs, model sizes, voice |
| v1 trigger | key/Enter (push-to-talk) | wake word deferred to Phase 5 |

## Proposed project layout

```
peruca-head/
├── CLAUDE.md
├── README.md
├── pyproject.toml            # deps + `peruca-head` entrypoint
├── .env.example              # PERUCA_API_URL, EXTERNAL_USER_ID, models, voice
├── src/peruca_head/
│   ├── __init__.py
│   ├── main.py               # main loop + state machine
│   ├── config.py             # pydantic settings
│   ├── audio/
│   │   ├── recorder.py       # capture + VAD
│   │   └── player.py         # playback
│   ├── stt.py                # faster-whisper wrapper
│   ├── tts.py                # Piper wrapper
│   ├── peruca_client.py      # HTTP client for /llm/chat
│   └── state.py              # IDLE/LISTENING/THINKING/SPEAKING (+ feedback)
└── tests/
    ├── test_peruca_client.py
    ├── test_state.py
    └── ...                   # mocks for audio / STT / TTS
```

### Component boundaries
- `peruca_client.py` — only place that knows the HTTP shape of `/llm/chat`. Owns
  ID handling (`external_user_id`, `chat_id`) and error/timeout handling.
- `audio/recorder.py` / `audio/player.py` — only places that touch `sounddevice`.
- `stt.py` / `tts.py` — only places that load the heavy models. Expose simple
  `transcribe(pcm) -> str` / `synthesize(text) -> pcm` style functions.
- `state.py` / `main.py` — orchestration only; no direct device or model access.

## Build plan (phased; each phase is independently testable)

Always build in this order — each phase produces something you can run.

- **Phase 0 — Skeleton.** `pyproject.toml`, `.env.example`, `src/` layout,
  `peruca_client` + test. Deliverable: a **text** chat in the terminal (type →
  peruca reply), no audio yet. Proves the API integration end-to-end.
- **Phase 1 — Voice output (TTS).** `tts.py` (Piper, pt-BR) + `player.py`.
  Deliverable: typed text is spoken in pt-BR; chain with Phase 0 (typed question →
  spoken answer).
- **Phase 2 — Voice input (capture + STT).** `recorder.py` (VAD) + `stt.py`.
  Deliverable: spoken phrase → correct text in the console.
- **Phase 3 — Full loop (push-to-talk).** `main.py` + `state.py` wiring
  `Enter/button → record → STT → peruca → TTS → speak → repeat`, with console
  state feedback and error handling (API down, empty transcript, timeout).
  Deliverable: end-to-end voice conversation triggered by a key.
- **Phase 4 — Robustness & config.** Everything in `.env` (URL, IDs, Whisper model
  size, Piper voice, VAD thresholds); start/stop cues; `peruca-head run` command;
  logging; `/health` check on startup. Deliverable: comfortable daily PC use.
- **Phase 5 — Wake word (optional, still on PC).** Always-on keyword detection
  (`openWakeWord`/Porcupine) replacing push-to-talk. Note: ready-made models are
  mostly English; a "peruca" wake word will likely need custom training — hence
  it is deferred.
- **Phase 6 — Hardware port (out of current scope; recorded for later).**
  Raspberry Pi (Zero 2 W / Pi 4) + mic (USB or I2S/ReSpeaker) + speaker (I2S
  MAX98357A or USB), LED ring for feedback, `systemd` autostart. Tune the Whisper
  model size to the Pi's CPU (likely `base`/`small`, or move STT to a server).

**Current status:** nothing implemented yet. The next step is **Phase 0**.

## Risks / things to watch
- **Whisper CPU latency** — start with `small`, measure before going bigger.
- **Piper pt-BR voice quality** — try 2–3 voices and pick one.
- **VAD vs. noise** — thresholds need tuning; noisy rooms degrade capture.
- **pt-BR wake word** — off-the-shelf models are English-centric; "peruca" likely
  needs custom training (why it's Phase 5).
- **User/session identity** — fixed `external_user_id` per device to start.

## Commands

> These reflect the planned layout; create them as Phase 0 lands.

```bash
# Setup (after pyproject.toml exists)
pip install -e .

# Run the voice loop (Phase 3+)
peruca-head run            # or: python -m peruca_head.main

# Tests (TDD — must stay green)
python -m pytest tests/ -v
python -m pytest tests/test_peruca_client.py -v

# Requires a running peruca for live use (not for unit tests):
#   cd ../peruca && docker compose up   (API on http://localhost:8000)
```
