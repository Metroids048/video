from avs.qa.audio_levels import audio_is_publishable


def test_rejects_missing_track():
    assert audio_is_publishable(has_audio=False, mean_db=-16.0, max_db=-1.5) is False


def test_rejects_practically_silent_track():
    assert audio_is_publishable(has_audio=True, mean_db=-80.0, max_db=-50.0) is False


def test_accepts_normalized_audible_track():
    assert audio_is_publishable(has_audio=True, mean_db=-18.0, max_db=-2.0) is True
