"""Unit tests for SpeakTextUseCase with Speaker and Player ports faked."""

from application.use_cases.speak_text import SpeakTextUseCase
from tests.fakes.fake_player import FakePlayer
from tests.fakes.fake_speaker import FakeSpeaker


def test_synthesizes_text_then_plays_the_buffer():
    speaker = FakeSpeaker()
    player = FakePlayer()
    use_case = SpeakTextUseCase(speaker=speaker, player=player)

    use_case.run("olá mundo")

    assert speaker.texts == ["olá mundo"]
    assert player.played == [speaker.buffer]


def test_blank_text_is_not_played():
    speaker = FakeSpeaker()
    player = FakePlayer()
    use_case = SpeakTextUseCase(speaker=speaker, player=player)

    use_case.run("   ")

    # An empty buffer carries nothing to play, so the player is never bothered.
    assert player.played == []
