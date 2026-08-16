import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / 'scripts' / 'build_ep01_information_guided_v4.py'
spec = importlib.util.spec_from_file_location('ep01_v4', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


class TimelineContractTests(unittest.TestCase):
    def test_segments_cover_master_audio_without_gaps_or_overlap(self):
        segments = mod.build_segments(39.5)
        mod.validate_segments(segments, 39.5)
        self.assertAlmostEqual(segments[0].out_start, 0.0, places=3)
        self.assertAlmostEqual(segments[-1].out_end, 39.5, places=3)
        for prev, cur in zip(segments, segments[1:]):
            self.assertAlmostEqual(prev.out_end, cur.out_start, places=3)

    def test_chapter_titles_are_transient_not_persistent(self):
        for chapter in mod.build_chapters():
            self.assertLessEqual(chapter.end - chapter.start, 1.8)

    def test_publishable_is_blocked_by_any_blocking_fail(self):
        statuses = {name: 'PASS' for name in mod.BLOCKING_STATUS_NAMES}
        self.assertEqual(mod.publishable_status(statuses), 'PASS')
        statuses['MOBILE_READABILITY'] = 'FAIL'
        self.assertEqual(mod.publishable_status(statuses), 'FAIL')

    def test_publish_master_targets_platform_safe_bitrate(self):
        self.assertEqual(mod.TARGET_VIDEO_BITRATE, "8M")

    def test_publish_master_enforces_cbr_floor_for_platform_transcode(self):
        self.assertEqual(mod.TARGET_VIDEO_MINRATE, "8M")
        self.assertIn("nal-hrd=cbr", mod.X264_CBR_PARAMS)
        self.assertIn("filler=1", mod.X264_CBR_PARAMS)

    def test_result_label_explicitly_says_demo(self):
        text = ' '.join(label.text for label in mod.build_labels())
        self.assertIn('模拟盘', text)
        self.assertIn('5000U', text)
        self.assertIn('7350U', text)


class VisualProgressRegressionTests(unittest.TestCase):
    def test_long_static_why_no_trade_span_is_split_into_real_progress_sources(self):
        segments = mod.build_segments(39.5)
        names = [s.name for s in segments]
        self.assertIn('why-no-trade-scroll', names)
        self.assertIn('exchange-rejection-proof', names)
        self.assertNotIn('why-no-trade-walkthrough', names)
        why = next(s for s in segments if s.name == 'why-no-trade-scroll')
        reject = next(s for s in segments if s.name == 'exchange-rejection-proof')
        self.assertLessEqual(why.out_end - why.out_start, 5.7)
        self.assertAlmostEqual(reject.source_start, 112.0, places=2)
        self.assertEqual(reject.crop_x, 700)

    def test_strategy_walkthrough_reaches_entry_and_exit_rules(self):
        segments = mod.build_segments(39.5)
        strategy = [s for s in segments if s.name.startswith('strategy-')]
        self.assertEqual([s.name for s in strategy], ['strategy-library-to-entry', 'strategy-entry-proof', 'strategy-exit-proof'])
        self.assertLessEqual(strategy[0].source_start, 64.8)
        self.assertGreaterEqual(strategy[-1].source_end, 72.59)
        self.assertTrue(all((s.out_end - s.out_start) <= 2.7 for s in strategy))

    def test_closing_uses_live_position_tp_sl_state(self):
        closing = next(s for s in mod.build_segments(39.5) if s.name == 'binance-dynamic-exit')
        self.assertAlmostEqual(closing.source_start, 129.0, places=2)
        self.assertAlmostEqual(closing.source_end, 134.08, places=2)
        self.assertEqual((closing.crop_x, closing.crop_w), (1450, 1100))

    def test_demo_result_is_broken_into_sub_three_second_real_binance_progress(self):
        result_segments = [s for s in mod.build_segments(39.5) if s.name.startswith('binance-demo-')]
        self.assertGreaterEqual(len(result_segments), 2)
        self.assertTrue(all((s.out_end - s.out_start) < 2.6 for s in result_segments))


if __name__ == '__main__':
    unittest.main()
