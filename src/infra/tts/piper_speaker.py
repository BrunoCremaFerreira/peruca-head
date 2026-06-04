"""PiperSpeaker: the Speaker adapter backed by Piper (pt-BR, local, CPU-friendly).

The only module aware of ``piper``. It translates Piper's stream of
``AudioChunk`` objects into a single domain :class:`AudioBuffer`, reading the
sample rate / channels / width from the chunks themselves (never hardcoding a
rate). ``piper`` is imported lazily and the voice is loaded once, so:

- importing this module needs no model on disk (unit tests inject a warm voice);
- the heavy ``PiperVoice.load`` runs once at startup (composition root), keeping
  it off the per-turn critical path.

Empty/blank text yields an empty buffer without calling Piper.
"""

from __future__ import annotations

from typing import Any, Optional

from domain.models.audio_buffer import AudioBuffer
from domain.ports.speaker import Speaker


class PiperSpeaker(Speaker):
    """Synthesizes pt-BR speech with a Piper voice."""

    def __init__(
        self,
        model_path: str,
        *,
        voice: Optional[Any] = None,
        length_scale: float = 1.0,
        voice_loader: Optional[Any] = None,
    ) -> None:
        """``model_path`` is the path to the ``.onnx`` (its ``.onnx.json`` must
        sit beside it). ``voice`` injects an already-loaded ``PiperVoice``
        (used by tests). ``voice_loader`` is a ``callable(model_path) -> voice``
        overriding how the voice is loaded (used by tests to avoid importing
        ``piper``); by default it lazily imports ``piper`` and calls
        ``PiperVoice.load``. ``length_scale`` > 1.0 slows speech down.
        """
        self._model_path = model_path
        self._voice = voice
        self._length_scale = length_scale
        self._voice_loader = voice_loader

    def warm_up(self) -> None:
        """Load the voice now (idempotent) so the first utterance is not slowed
        by model loading and a missing voice fails here, not mid-conversation."""
        self._loaded_voice()

    def synthesize(self, text: str) -> AudioBuffer:
        if text.strip() == "":
            return AudioBuffer.empty()

        voice = self._loaded_voice()
        syn_config = self._synthesis_config()
        if syn_config is None:
            chunks = list(voice.synthesize(text))
        else:
            chunks = list(voice.synthesize(text, syn_config=syn_config))

        if not chunks:
            return AudioBuffer.empty()

        pcm = b"".join(chunk.audio_int16_bytes for chunk in chunks)
        first = chunks[0]
        return AudioBuffer(
            pcm=pcm,
            sample_rate=first.sample_rate,
            channels=first.sample_channels,
            sample_width=first.sample_width,
        )

    def _loaded_voice(self) -> Any:
        if self._voice is None:
            self._voice = self._load(self._model_path)
        return self._voice

    def _load(self, model_path: str) -> Any:
        if self._voice_loader is not None:
            return self._voice_loader(model_path)
        from piper import PiperVoice

        return PiperVoice.load(model_path)

    def _synthesis_config(self) -> Optional[Any]:
        if self._length_scale == 1.0:
            return None
        from piper import SynthesisConfig

        return SynthesisConfig(length_scale=self._length_scale)
