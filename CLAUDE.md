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
- **Always write all documentation, comments, and code in English** — without
  exception. (User-facing voice text is pt-BR; that is data/config, not code.)
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

## Project layout (Clean Architecture + DDD)

The head is a thin, I/O-bound application: its value is **orchestrating four heavy
external dependencies (audio, STT, TTS, HTTP) at low latency without coupling to any
of them** — the business logic lives in `../peruca`. Clean Architecture here serves
two concrete goals (not purity): (1) test the whole thing without hardware, models, or
network — already a CLAUDE.md requirement; (2) swap implementations (Whisper → other
STT, Piper → other TTS, push-to-talk → wake word) without touching orchestration.

The layer vocabulary mirrors the sibling `../peruca` (`domain` / `application` /
`infra` / `tests`) so navigating between both projects uses the same mental map.

```
peruca-head/
├── CLAUDE.md · README.md
├── pyproject.toml                    # deps + `peruca-head` entrypoint
├── .env.example                      # PERUCA_API_URL, EXTERNAL_USER_ID, models, voice, VAD
└── src/                              # the package root itself (mirrors ../peruca/src)
    ├── domain/                        # core — imports NOTHING external
    │   ├── models/                    #   value objects / entities of the voice domain
    │   │   ├── audio_buffer.py            # VO: PCM samples + sample_rate + channels (immutable)
    │   │   ├── transcript.py              # VO: recognised text (+ is_empty())
    │   │   ├── reply.py                   # VO: textual reply from the brain
    │   │   └── conversation.py            # Entity: ConversationSession (external_user_id, chat_id)
    │   └── ports/                     #   interfaces (ABC/Protocol) = the contracts
    │       ├── recorder.py                # Recorder
    │       ├── player.py                  # Player
    │       ├── transcriber.py             # Transcriber
    │       ├── speaker.py                 # Speaker
    │       └── brain_client.py            # BrainClient
    ├── application/                   # use cases — depends only on domain
    │   ├── use_cases/
    │   │   └── voice_turn.py              # VoiceTurnUseCase: one turn (record→…→play)
    │   └── voice_loop.py                  # VoiceLoop: state machine that repeats the turn
    ├── infra/                         # adapters — the ONLY place that touches external libs
    │   ├── audio/
    │   │   ├── sounddevice_recorder.py       # SoundDeviceRecorder (Recorder + VAD)
    │   │   └── sounddevice_player.py         # SoundDevicePlayer (Player)
    │   ├── stt/
    │   │   └── whisper_transcriber.py        # WhisperTranscriber (Transcriber)
    │   ├── tts/
    │   │   └── piper_speaker.py              # PiperSpeaker (Speaker)
    │   └── brain/
    │       └── http_peruca_client.py         # HttpPerucaClient (BrainClient)
    ├── config.py                      # pydantic-settings: single source of config (.env)
    ├── composition.py                 # composition root: builds and injects the adapters
    ├── main.py                        # CLI entrypoint: read config → composition → run loop
    └── tests/                         # mirrors the layers (tests live inside src/)
        ├── conftest.py
        ├── fakes/                     # fakes of the PORTS (reusable across tests)
        │   ├── fake_recorder.py · fake_player.py
        │   ├── fake_transcriber.py · fake_speaker.py
        │   └── fake_brain_client.py
        ├── unit_tests/
        │   ├── domain/                # VOs/entity: immutability, equality, invariants
        │   ├── application/           # use cases & voice_loop with ALL ports faked
        │   └── infra/                 # each adapter with its OWN lib mocked (sd/whisper/piper/httpx)
        └── integration_tests/         # contract with real peruca (opt-in, @pytest.mark.integration)
```

### Ports and concrete adapters

Each port speaks in **domain value objects**, never in library types (faster-whisper
segments, `httpx.Response`, raw arrays). That is what keeps the contract stable when a
library changes. Ports are granular per capability (Interface Segregation):

| Port (`domain/ports/`) | Conceptual signature | Adapter (`infra/`) | Isolated lib |
|---|---|---|---|
| `Recorder` | `record_until_silence() -> AudioBuffer` | `SoundDeviceRecorder` | `sounddevice` + VAD |
| `Transcriber` | `transcribe(AudioBuffer) -> Transcript` | `WhisperTranscriber` | `faster_whisper` |
| `BrainClient` | `ask(message, ConversationSession) -> Reply` | `HttpPerucaClient` | `httpx` |
| `Speaker` | `synthesize(text) -> AudioBuffer` | `PiperSpeaker` | `piper` |
| `Player` | `play(AudioBuffer) -> None` | `SoundDevicePlayer` | `sounddevice` |

`Recorder` and `Player` are separate ports even though both use `sounddevice` —
capturing and playing are distinct responsibilities, mocked independently. The trigger
(push-to-talk / wake word) is a Strategy: in Phase 3 it is just `main` waiting for
Enter; a `Trigger` port + wake-word adapter only arrives in Phase 5 (YAGNI until then).

### Dependency rule (who may import whom)

Dependencies always point inward (Dependency Inversion):

1. **`domain/` imports nothing** — not `application`, not `infra`, not external libs
   (`sounddevice`, `faster_whisper`, `piper`, `httpx`). Innermost ring.
2. **`application/` imports only `domain/`.** Never `infra`, never an external lib.
   (Fitness check: `grep` for those imports under `application/` must return zero.)
3. **`infra/` imports `domain/`** (to implement ports and return VOs) and the external
   libs. Adapters never import one another.
4. **Only the composition root (`composition.py`) knows the concrete adapters** and
   instantiates them.

**Why this protects latency:** the composition root loads Whisper and Piper **once** at
startup and injects already-warm instances; since use cases see only ports, there is no
way to instantiate a model per request on the critical path
(record→stt→ask→tts→play). **Why it protects decoupling:** swapping STT/TTS or
push-to-talk→wake word is one new adapter plus one line in the composition root; the
Raspberry Pi port (Phase 6) is new audio adapters with the same orchestration.

### Component mapping (old single-file plan → layered structure)

| Concern | Lives in | Notes |
|---|---|---|
| HTTP shape of `/llm/chat`, ID handling, error/timeout | port `BrainClient` + `infra/brain/http_peruca_client.py` | HTTP shape never leaks out of infra |
| audio capture + VAD | port `Recorder` + `infra/audio/sounddevice_recorder.py` | only place touching `sounddevice` (capture) |
| audio playback | port `Player` + `infra/audio/sounddevice_player.py` | only place touching `sounddevice` (output) |
| STT (heavy model) | port `Transcriber` + `infra/stt/whisper_transcriber.py` | only place loading Whisper |
| TTS (heavy model) | port `Speaker` + `infra/tts/piper_speaker.py` | only place loading Piper |
| state machine IDLE/LISTENING/THINKING/SPEAKING | `application/voice_loop.py` | orchestration only; no device/model access |
| one turn of the loop | `application/use_cases/voice_turn.py` | testable unit; covers empty transcript, brain error/timeout |
| wiring + entrypoint | `composition.py` + `main.py` | composition root separate from CLI entrypoint |

### Pragmatic start (Phase 0)

Clean Architecture is justified here because the mandatory "test without external
dependencies" already forces ports + adapters + fakes — ~80% of the cost is paid
regardless. The over-engineering risk lives only in *folder depth and domain richness*,
so grow it **per phase**: for Phase 0 (text-only terminal chat) implement just the
vertical slice that proves the brain integration — `domain/models/{reply,conversation}`,
`domain/ports/brain_client.py`, `infra/brain/http_peruca_client.py`, a minimal
text→text use case, `config.py`, `composition.py`, `main.py`, plus
`tests/fakes/fake_brain_client.py` and unit tests. Do **not** create `audio/`, `stt/`,
`tts/`, `AudioBuffer`, `Transcript`, or `VoiceLoop` yet — they land in Phases 1–3, each
as a port+adapter pair, with no refactor of the foundation. Keep `AudioBuffer` a thin VO
(no DSP in the domain).

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

**Current status:** **Phases 0, 1 and 2 done.** Phase 0 — text chat against
peruca's `/llm/chat` (`httpx` mocked via `respx`, brain faked). Phase 1 — voice
output: `AudioBuffer` VO, `Speaker`/`Player` ports, `PiperSpeaker` (Piper) and
`SoundDevicePlayer` (sounddevice) adapters. Phase 2 — voice input: `Transcript`
VO, `Recorder`/`Transcriber` ports, `SoundDeviceRecorder` (sounddevice + silero
VAD, record-until-silence) and `WhisperTranscriber` (faster-whisper) adapters;
`peruca-head listen` records a phrase and prints the pt-BR transcript
(`cientista`-validated). All adapters lazy-load and mock their heavy libs, so
every unit test runs with no network, model, or hardware. The next step is
**Phase 3 (Full loop — push-to-talk)**, which composes Phases 0–2 into one turn.

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
peruca-head run            # or: python src/main.py

# Tests (TDD — must stay green). Tests live inside src/ (src/tests/)
python -m pytest src/tests/ -v
python -m pytest src/tests/unit_tests/ -v                  # fast, no external deps
python -m pytest src/tests/integration_tests/ -v -m integration   # needs a running peruca

# Requires a running peruca for live use (not for unit tests):
#   cd ../peruca && docker compose up   (API on http://localhost:8000)
```
