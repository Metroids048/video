from avs.qa.audio_levels import parse_mean_volume, parse_max_volume


def test_parse_audio_levels_from_ffmpeg_output():
    text = 'mean_volume: -17.0 dB\nmax_volume: -1.1 dB\n'
    assert parse_mean_volume(text) == -17.0
    assert parse_max_volume(text) == -1.1
