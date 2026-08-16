import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / 'scripts' / 'qa_ep01_information_guided_v4.py'
spec = importlib.util.spec_from_file_location('ep01_v4_qa', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class QaContractTests(unittest.TestCase):
    def sample_probe(self):
        return {'streams': [
            {'codec_type':'video','codec_name':'h264','profile':'High','width':1080,'height':1920,
             'pix_fmt':'yuv420p','r_frame_rate':'30/1','start_time':'0.000000','duration':'39.500000','bit_rate':'7960117'},
            {'codec_type':'audio','codec_name':'aac','sample_rate':'48000','channels':2,
             'start_time':'0.000000','duration':'39.484000','bit_rate':'193278'}],
            'format': {'duration':'39.500000','bit_rate':'8162521'}}

    def test_technical_contract_accepts_target_master(self):
        result = mod.evaluate_technical(self.sample_probe(), decode_error_bytes=0, black_intervals=[])
        self.assertEqual(result['status'], 'PASS')
        self.assertLessEqual(result['av_end_delta_ms'], 50)

    def test_technical_contract_rejects_low_video_bitrate(self):
        probe = self.sample_probe()
        probe['streams'][0]['bit_rate'] = '500000'
        result = mod.evaluate_technical(probe, decode_error_bytes=0, black_intervals=[])
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('video_bitrate_below_6mbps', result['failures'])

    def test_freeze_findings_are_diagnostic_not_automatic_publish_fail(self):
        review = mod.evaluate_visual_review(freezes=[{'start':0.0,'end':4.36,'duration':4.36}],
            manual_continuity_pass=True, mobile_readability_pass=True,
            notes=['real state progression remains visible'])
        self.assertEqual(review['VISUAL_CONTINUITY'], 'PASS')
        self.assertEqual(review['MOBILE_READABILITY'], 'PASS')
        self.assertEqual(review['freeze_policy'], 'diagnostic_only')

    def test_publishable_fails_if_any_blocking_dimension_fails(self):
        statuses = {name: 'PASS' for name in mod.BLOCKING_STATUS_NAMES}
        self.assertEqual(mod.publishable(statuses), 'PASS')
        statuses['AUDIO_VISUAL_SEMANTIC_SYNC'] = 'FAIL'
        self.assertEqual(mod.publishable(statuses), 'FAIL')

    def test_loudness_contract_accepts_locked_v3_mix(self):
        self.assertEqual(mod.evaluate_audio({'input_i':-14.24,'input_tp':-1.05,'input_lra':3.6})['status'], 'PASS')


if __name__ == '__main__':
    unittest.main()
