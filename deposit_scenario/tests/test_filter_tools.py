import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from filter_tools import HERE, assert_filter_active, cases, retire_legacy
from rpc_client import FILTER, LEGACY_FILTER


class UpgradeTests(unittest.TestCase):
    def bank(self, names):
        bank = Mock()
        self.names = set(names)

        def call(method, *args):
            if method == "liststreams":
                return [{"filters": [{"name": name} for name in self.names]}]
            if method == "getfiltercode":
                filename = "bank_filter.js" if args[0] == FILTER else "bank_filter_legacy.js"
                return (HERE / filename).read_text(encoding="utf-8")
            if method == "approvefrom":
                self.assertEqual(args[1:], (LEGACY_FILTER, {"for": "bank_events", "approve": False}))
                self.names.remove(LEGACY_FILTER)
                return "a" * 64
            raise AssertionError(method)

        bank.call.side_effect = call
        return bank

    def test_legacy_rule_blocks_new_workflow_until_retired(self):
        with self.assertRaisesRegex(ValueError, "Other active bank filters"):
            assert_filter_active(self.bank([FILTER, LEGACY_FILTER]))

    @patch("filter_tools.save_filter")
    @patch("filter_tools.wait_confirmed", return_value=1)
    def test_upgrade_requires_new_active_filter_before_disapproving_old(self, wait, save):
        bank = self.bank([LEGACY_FILTER])
        with self.assertRaisesRegex(ValueError, "not active"):
            retire_legacy(bank, "public-bank-address")
        self.assertFalse(any(call.args[0] == "approvefrom" for call in bank.call.call_args_list))

    @patch("filter_tools.save_filter")
    @patch("filter_tools.wait_confirmed", return_value=1)
    def test_retires_only_known_old_rule_with_replacement_already_active(self, wait, save):
        bank = self.bank([FILTER, LEGACY_FILTER])
        report = retire_legacy(bank, "public-bank-address")
        self.assertTrue(report["retired"])
        self.assertEqual(self.names, {FILTER})
        self.assertFalse(report["old_filter_and_history_deleted"])
        save.assert_called_once()

    def test_repeated_retirement_is_read_only(self):
        bank = self.bank([FILTER])
        self.assertTrue(retire_legacy(bank, "public-bank-address")["already_inactive"])
        self.assertFalse(any(call.args[0] == "approvefrom" for call in bank.call.call_args_list))

    def test_unknown_filter_is_not_silently_removed(self):
        bank = self.bank([FILTER, LEGACY_FILTER, "someone_elses_rule"])
        with self.assertRaisesRegex(ValueError, "Other active bank filters"):
            retire_legacy(bank, "public-bank-address")
        self.assertFalse(any(call.args[0] == "approvefrom" for call in bank.call.call_args_list))

    def test_deployed_code_mismatch_stops_publication(self):
        bank = self.bank([FILTER])
        original = bank.call.side_effect
        bank.call.side_effect = lambda method, *args: "wrong code" if method == "getfiltercode" else original(method, *args)
        with self.assertRaisesRegex(ValueError, "differs"):
            assert_filter_active(bank)

    def test_changed_legacy_code_is_not_disapproved(self):
        bank = self.bank([FILTER, LEGACY_FILTER])
        original = bank.call.side_effect
        bank.call.side_effect = lambda method, *args: "changed legacy code" if method == "getfiltercode" and args[0] == LEGACY_FILTER else original(method, *args)
        with self.assertRaisesRegex(ValueError, "Legacy deployed code differs"):
            retire_legacy(bank, "public-bank-address")
        self.assertFalse(any(call.args[0] == "approvefrom" for call in bank.call.call_args_list))

    def test_tests_cover_old_rates_and_correct_forty_percent_arithmetic(self):
        fixtures = {name: (payload, expected) for name, payload, expected in cases()}
        self.assertEqual(fixtures["valid"][0]["bonus_percent"], 40)
        self.assertEqual(fixtures["valid"][0]["final_amount"], 1400)
        for name in ("rate_50_rejected", "rate_60_rejected"):
            self.assertEqual(fixtures[name][1], "bonus_percent must be 40")
        self.assertTrue(all(payload["offer_id"].startswith("TEST40_") for payload, _ in fixtures.values()))


if __name__ == "__main__":
    unittest.main()
