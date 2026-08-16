import inspect

from avs.qa import report


def test_run_qa_contains_release_blocking_audible_audio_gate():
    source = inspect.getsource(report.run_qa)
    assert 'audio_audible' in source
    assert 'audio_is_publishable' in source
    assert '音轨存在但实际响度不可听' in source
