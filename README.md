# Peruca Head

**The voice device for the [Peruca](../peruca) assistant — a self-hosted, Echo Dot-like "head".**

Peruca Head is the **voice client**. It holds no intelligence of its own: the brain
already exists in the sibling project [`peruca`](../peruca), which exposes a REST API
(`POST /llm/chat`). The head's only job is to close the **voice loop** around that
API — listen, transcribe, ask Peruca, speak the answer.

> **Status:** **Phases 0–5 implemented** — the PC voice loop is feature-complete.
> Phase 0 — text chat. Phase 1 — voice output (Piper). Phase 2 — voice input
> (silero VAD + faster-whisper). Phase 3 — full push-to-talk loop. Phase 4 —
> robustness & config (`peruca-head run`, start-cue beep, `/health` check,
> logging, full `.env`). Phase 5 — wake word: a pluggable `Trigger` strategy
> (push-to-talk by default; openWakeWord when a model is supplied). All fully
> unit-tested with no network, model, or hardware. Only the Raspberry Pi port
> (Phase 6) remains, and is out of current scope. See [`CLAUDE.md`](CLAUDE.md).

---

## How it works

```
[wake word / push-to-talk]
   → audio capture (VAD: record until silence)
       → STT, local (faster-whisper, pt-BR) ........ audio → text
           → POST /llm/chat (peruca) ................ text → reply
               → TTS, local (Piper, pt-BR) .......... reply → audio
                   → play on speaker
                       → back to IDLE
```

The brain (intent routing, smart home, shopping list, conversation, memory) lives in
Peruca. The head only handles **voice in → text → voice out**.

## Design decisions

- **Target — PC first.** Everything is developed and validated on a laptop/PC (its
  own mic and speaker). Porting to a Raspberry Pi is a later phase and is kept out of
  scope until the PC loop is solid.
- **STT/TTS — 100% local.** No cloud. This matches Peruca's self-hosted philosophy.
  CPU-only must work; a GPU only accelerates Whisper.
- **Language — pt-BR** across the whole chain (STT, TTS, and eventually the wake
  word). User-facing speech is Portuguese; all source code is English.

## The Peruca API contract

The head talks to a running Peruca instance:

```
POST http://localhost:8000/llm/chat
  body:  { "message": str, "external_user_id": str, "chat_id": str }
  reply: { "response": str, "external_user_id": str, "chat_id": str }

GET  /health → { "status": "ok" }
```

- `external_user_id` identifies the user — Peruca keeps **per-user persistent
  memory**, so it must be stable for a given device.
- `chat_id` keeps a conversation thread together.
- The head generates and persists both IDs locally. For now the device is
  single-user with a fixed `external_user_id`.

## Architecture (Clean Architecture + Ports & Adapters)

Dependencies point **inward**: `domain` imports nothing, `application` imports only
`domain`, and `infra` (the adapters) is the single place allowed to touch each
external library. The composition root is the only module that knows the concrete
adapters and wires them together.

```
src/
├── main.py                       ← CLI entrypoint: run / loop / listen / chat
├── composition.py                ← composition root: builds & injects the adapters
├── config.py                     ← settings (pydantic-settings); single source of config
├── domain/                       ← core — imports nothing external
│   ├── models/                   ←   value objects & entities
│   │   ├── audio_buffer.py · transcript.py · reply.py
│   │   ├── conversation.py · turn_outcome.py · voice_state.py
│   └── ports/                    ←   the contracts (ABC/Protocol)
│       ├── recorder.py · transcriber.py · speaker.py · player.py
│       ├── brain_client.py · brain_health.py · trigger.py
├── application/                  ← use cases — depends only on domain
│   ├── use_cases/
│   │   ├── text_turn.py · listen.py · speak_text.py
│   │   ├── voice_turn.py · check_brain_health.py
│   └── voice_loop.py             ←   state machine IDLE/LISTENING/THINKING/SPEAKING
├── infra/                        ← adapters — the ONLY place that touches external libs
│   ├── audio/
│   │   ├── sounddevice_recorder.py   ← capture + VAD (sounddevice + silero)
│   │   ├── sounddevice_player.py     ← playback (sounddevice)
│   │   └── cue_factory.py            ← start-cue beep generator
│   ├── stt/whisper_transcriber.py    ← faster-whisper
│   ├── tts/piper_speaker.py          ← Piper
│   ├── brain/http_peruca_client.py   ← httpx adapter for /llm/chat
│   └── trigger/
│       ├── enter_trigger.py          ← push-to-talk (Enter)
│       └── wakeword_trigger.py       ← openWakeWord (optional, lazy-loaded)
└── tests/                        ← mirrors the layers (fakes/ unit_tests/ integration_tests/)
```

- Only `infra/audio/` imports `sounddevice`; only `infra/stt/` loads Whisper; only
  `infra/tts/` loads the Piper voice; only `infra/brain/` knows the HTTP shape of
  `/llm/chat`. Adapters never import one another.
- The composition root loads Whisper and Piper **once** at startup and injects
  already-warm instances, keeping the heavy models off the per-turn critical path
  (record → STT → ask → TTS → play).
- `config.py` is the single source of configuration — no hardcoded URLs, IDs, model
  sizes, voices, or VAD thresholds anywhere else.

## Tech stack

| Concern | Library | Notes |
|---|---|---|
| Audio I/O | `sounddevice` (PortAudio) | PCM capture and playback |
| Voice activity (VAD) | `silero-vad` (or `webrtcvad`) | record until silence |
| STT | `faster-whisper` (CTranslate2) | model `small`/`medium`, `language="pt"` |
| HTTP | `httpx` | calls `/llm/chat` |
| TTS | `piper-tts` | pt-BR voice (e.g. `pt_BR-faber-medium`) |
| Config | `pydantic-settings` + `.env` | API URL, IDs, model sizes, voice |
| v1 trigger | key/Enter (push-to-talk) | wake word deferred to Phase 5 |

## Development conventions

This project follows the same discipline as Peruca (see [`CLAUDE.md`](CLAUDE.md) for
the full rules):

- **TDD is mandatory — no exceptions.** Nothing is implemented before its tests are
  written first, for new features, changes, *and* bug fixes (RED → GREEN → REFACTOR).
- **All code in English.** User-facing pt-BR text is data/config, not code.
- **Never commit automatically** — only when explicitly requested.
- **No test may require** a real microphone, speaker, model download, or a running
  Peruca instance. All external dependencies are mocked behind their ports.

### Specialized agents (`.claude/agents/`)

| Agent | Role |
|---|---|
| `cientista` | ML / LLM / STT / TTS specialist (advisory). Must validate any plan or change affecting models, STT, TTS, VAD, audio, wake word, latency, or quality — before and after implementation. |
| `arquiteto` | Software architect (advisory). Design, boundaries, layering, patterns. |
| `programador-tester` | Writes the failing test first (TDD). |
| `programador` | Implements the minimum to pass an existing test, then refactors. |

Consultation order for ML/audio features:
`cientista` → `arquiteto` → `programador-tester` → `programador` → `cientista`.

## Build plan

Each phase is independently runnable. **Phases 0–5 are done**; only the Raspberry Pi
port (Phase 6) remains, and is out of current scope.

| Phase | Goal | Done when |
|---|---|---|
| **0 ✅** | Skeleton + brain client | Text chat in the terminal (type → Peruca reply), no audio |
| **1 ✅** | Voice output (TTS) | Typed text is spoken in pt-BR |
| **2 ✅** | Voice input (capture + STT) | Spoken phrase → correct text in console |
| **3 ✅** | Full loop (push-to-talk) | End-to-end voice conversation, triggered by a key |
| **4 ✅** | Robustness & config | Comfortable daily PC use; `.env`-driven; `/health` check |
| **5 ✅** | Wake word (optional) | Pluggable trigger; openWakeWord when a model is supplied |
| **6 ⬜** | Hardware port (out of scope for now) | Runs on a Raspberry Pi with mic, speaker, LED |

## Getting started

**Prerequisites**

- Python 3.11+
- A running Peruca instance reachable on `http://localhost:8000`
  (`cd ../peruca && docker compose up`)
- PortAudio (for `sounddevice`, needed to play audio) —
  e.g. `sudo apt install libportaudio2`. Not required to run the tests.
- For voice output: a pt-BR Piper voice on disk (the `.onnx` plus its
  `.onnx.json`), e.g. `pt_BR-faber-medium`.

**Install**

```bash
pip install -e .
cp .env.example .env      # then edit PERUCA_API_URL, EXTERNAL_USER_ID, etc.
```

**Run**

```bash
peruca-head               # the voice head (= `run`); needs TTS configured
peruca-head chat          # text-only chat; type a message, get Peruca's reply
```

To also hear replies spoken (Phase 1), set in `.env`:

```ini
TTS_ENABLED=true
PIPER_VOICE_PATH=/path/to/pt_BR-faber-medium.onnx
```

To try voice input (Phase 2) — record a phrase and see the transcript:

```bash
peruca-head listen        # speak; Ctrl-C to stop
```

The first run downloads the faster-whisper model named by `WHISPER_MODEL_SIZE`
(`small` by default). silero-vad pulls in PyTorch.

To run the full voice conversation (Phases 3–4) — needs TTS configured (the loop
and its error messages are spoken):

```bash
peruca-head run           # Enter → beep → speak → hear the reply → repeat; Ctrl-C to stop
```

A short beep means "you can speak" — **speak after the beep** (audio captured
during the cue is not recorded). On startup the head probes the brain's
`/health`; if it's down it warns and starts anyway (the first turn will speak the
error). Set `AUDIO_CUES_ENABLED=false` to silence the beep.

To replace push-to-talk with an always-on wake word (Phase 5, optional), set
`TRIGGER_TYPE=wake_word` and `WAKE_WORD_MODEL_PATH=/path/to/model.onnx`. Stock
openWakeWord models are English (e.g. `hey_jarvis`) — recognizing "peruca"
requires a custom-trained pt-BR model, which is why push-to-talk is the default.

**Test** — fast, no network/model/hardware:

```bash
python -m pytest src/tests/ -v
python -m pytest src/tests/unit_tests/ -v
python -m pytest src/tests/integration_tests/ -v -m integration   # needs a live Peruca
```

## Configuration

All configuration lives in `.env` (loaded via `config.py`); copy
[`.env.example`](.env.example) and edit. The main keys:

```ini
# Brain API & identity
PERUCA_API_URL=http://localhost:8000
EXTERNAL_USER_ID=peruca-head-device   # stable per device; keys Peruca's per-user memory
CHAT_ID=peruca-head-session           # conversation thread id
REQUEST_TIMEOUT_SECONDS=30

# Voice output (TTS, Phase 1) — disabled by default so text chat needs no voice on disk
TTS_ENABLED=false
PIPER_VOICE_PATH=                     # path to the pt-BR Piper .onnx (its .onnx.json beside it)
PIPER_LENGTH_SCALE=1.0                # > 1.0 slows speech, < 1.0 speeds it up

# Voice input (STT + VAD, Phase 2)
WHISPER_MODEL_SIZE=small              # faster-whisper model, downloaded on first use
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
STT_LANGUAGE=pt
VAD_MIN_SILENCE_MS=800                # silence that ends a recording
VAD_MAX_RECORDING_MS=15000

# Robustness & feedback (Phase 4)
LOG_LEVEL=INFO
AUDIO_CUES_ENABLED=true               # short "you can speak" beep before recording
HEALTH_CHECK_ENABLED=true             # /health probe on startup (warn & continue if down)

# Trigger / wake word (Phase 5, optional)
TRIGGER_TYPE=enter                    # "enter" = push-to-talk; "wake_word" = always-on
WAKE_WORD_MODEL_PATH=                 # required when TRIGGER_TYPE=wake_word
WAKE_WORD_THRESHOLD=0.5
```

See [`.env.example`](.env.example) for the complete list (VAD frame/threshold
tuning, cue frequency/volume, beam size, capture rate, refractory window, …).

## Relationship to Peruca

```
┌──────────────┐   POST /llm/chat    ┌──────────────┐
│ peruca-head  │ ──────────────────► │    peruca    │
│ (this repo)  │ ◄────────────────── │  (the brain) │
│  voice I/O   │     reply text      │  FastAPI API │
└──────────────┘                     └──────────────┘
```

The contract source of truth is in Peruca:
`../peruca/src/application/appservices/view_models.py` (`ChatRequest`,
`ChatResponse`) and its `routes.py`.

