import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo import Demo, amounts, body, digest, index_records
from rpc_client import BANK, USER, credentials


def record(payload, digit="a"):
    return {"txid": digit * 64, "vout": 0, "data": {"json": payload}, "available": True}


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.offer = dict(schema_version=1, offer_id="DEP001", user_id=USER,
                          principal=1000, bonus_percent=40, maturity_months=6,
                          event="DEPOSIT_OFFERED", status="OFFERED", actor_role="BANK",
                          source_chain=BANK, destination_chain=USER)

    def test_main_calculation(self):
        self.assertEqual(amounts(1000, 40), (400, 1400))

    def test_user_selected_amount(self):
        self.assertEqual(amounts(2500, 40), (1000, 3500))

    def test_invalid_amounts(self):
        for principal, percent in [(0, 40), (-1, 40), (True, 40), (1.5, 40),
                                    (1000, 50), (1000, 60), (1000, 55), (1000, True),
                                    (1, 40), (10**10, 40)]:
            with self.assertRaises(ValueError):
                amounts(principal, percent)

    def test_hash_is_canonical(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))
        self.assertNotEqual(digest({"a": 1}), digest({"a": 2}))

    def test_duplicate_stream_event_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            index_records([record(self.offer), record(self.offer, "b")], "DEP001")

    def test_unavailable_record_fails_closed(self):
        with self.assertRaises(ValueError):
            body({"available": False, "data": None})

    def test_identical_user_acceptance_replay_processed_once(self):
        consent = dict(self.offer, event="DEPOSIT_ACCEPTED", status="ACCEPTED", acceptance="ACCEPT")
        indexed = index_records([record(consent, "a"), record(consent, "b")], "DEP001", True)
        self.assertEqual(len(indexed), 1)
        self.assertEqual(indexed["DEPOSIT_ACCEPTED"]["txid"], "a" * 64)
        self.assertEqual(indexed["DEPOSIT_ACCEPTED"]["identical_replay_txids"], ["b" * 64])

    def test_conflicting_user_acceptance_replay_rejected(self):
        consent = dict(self.offer, event="DEPOSIT_ACCEPTED", acceptance="ACCEPT")
        conflict = dict(consent, principal=2000)
        with self.assertRaises(ValueError):
            index_records([record(consent, "a"), record(conflict, "b")], "DEP001", True)

    def test_bank_acceptance_duplicates_are_not_silently_collapsed(self):
        consent = dict(self.offer, event="DEPOSIT_ACCEPTED", acceptance="ACCEPT")
        with self.assertRaises(ValueError):
            index_records([record(consent, "a"), record(consent, "b")], "DEP001", False)

    def test_wrong_offer_key_rejected(self):
        with self.assertRaises(ValueError):
            index_records([record(self.offer)], "OTHER")

    def test_immutable_terms(self):
        helper = Demo(clients={BANK: Mock(), USER: Mock()})
        changed = copy.deepcopy(self.offer)
        changed["principal"] = 2000
        with self.assertRaisesRegex(ValueError, "Terms differ"):
            helper.check_terms(record(changed), record(self.offer))

    def test_relay_reference_checked_against_source(self):
        helper = Demo(clients={BANK: Mock(), USER: Mock()})
        source = record(self.offer)
        copied = copy.deepcopy(self.offer)
        copied["relay_ref"] = helper.proof(BANK, source)
        helper.verify_relay(record(copied, "b"), source, BANK)
        copied["relay_ref"]["payload_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            helper.verify_relay(record(copied, "b"), source, BANK)

    def test_completion_cannot_precede_acceptance(self):
        bank, user = Mock(), Mock()
        bank.call.return_value = [record(self.offer)]
        user.call.return_value = []
        helper = Demo(clients={BANK: bank, USER: user})
        with self.assertRaisesRegex(ValueError, "Missing DEPOSIT_ACCEPTED"):
            helper.complete("DEP001")
        self.assertFalse(any(call.args[0] == "publishfrom" for call in bank.call.call_args_list))

    def test_missing_vout_resolved_from_real_transaction_shape(self):
        bank = Mock()
        bank.call.return_value = {"vout": [{"n": 2, "items": [{"name": "bank_events", "data": {"json": self.offer}}]}]}
        helper = Demo(clients={BANK: bank, USER: Mock()})
        source = record(self.offer)
        del source["vout"]
        self.assertEqual(helper.proof(BANK, source)["vout"], 2)

    def test_ambiguous_output_stops_relay(self):
        bank = Mock()
        output = {"n": 0, "items": [{"name": "bank_events", "data": {"json": self.offer}}]}
        bank.call.return_value = {"vout": [output, output]}
        helper = Demo(clients={BANK: bank, USER: Mock()})
        source = record(self.offer)
        del source["vout"]
        with self.assertRaises(ValueError):
            helper.proof(BANK, source)

    def test_duplicate_publish_does_not_send_again(self):
        bank = Mock()
        bank.call.return_value = [record(self.offer)]
        helper = Demo(clients={BANK: bank, USER: Mock()})
        result = helper.publish(BANK, self.offer)
        self.assertEqual(result["txid"], "a" * 64)
        self.assertEqual([call.args[0] for call in bank.call.call_args_list], ["liststreamkeyitems"])

    def accepted_fixture(self):
        bank, user = Mock(), Mock()
        helper = Demo(clients={BANK: bank, USER: user})
        offered = record(self.offer, "a")
        user_offer = dict(self.offer, relay_ref=helper.proof(BANK, offered))
        consent = helper.make(offered, "DEPOSIT_ACCEPTED")
        consent.update(acceptance="ACCEPT", acknowledges_txid=offered["txid"])
        user_accept = record(consent, "b")
        bank_accept = record(dict(consent, relay_ref=helper.proof(USER, user_accept)), "c")
        maturity = record(helper.make(offered, "MATURITY_REACHED"), "d")
        user_maturity = record(dict(body(maturity), relay_ref=helper.proof(BANK, maturity)), "e")
        state = {BANK: {"DEPOSIT_OFFERED": offered, "DEPOSIT_ACCEPTED": bank_accept, "MATURITY_REACHED": maturity},
                 USER: {"DEPOSIT_OFFERED": record(user_offer), "DEPOSIT_ACCEPTED": user_accept, "MATURITY_REACHED": user_maturity}}
        helper.events = Mock(side_effect=lambda chain, offer: state[chain])
        return helper, state

    def test_completion_requires_bonus_acceptance_even_after_maturity(self):
        helper, state = self.accepted_fixture()
        with self.assertRaisesRegex(ValueError, "Missing BONUS_ACCEPTED"):
            helper.complete("DEP001")
        self.assertEqual(helper.clients[BANK].call.call_count, 0)

    def test_bonus_acceptance_cannot_precede_maturity_notice(self):
        helper, state = self.accepted_fixture()
        del state[USER]["MATURITY_REACHED"]
        with self.assertRaisesRegex(ValueError, "Missing MATURITY_REACHED"):
            helper.acceptance_payload("DEP001", bonus=True)

    def test_completed_offer_is_not_credited_twice(self):
        helper, state = self.accepted_fixture()
        original = state[BANK]["DEPOSIT_OFFERED"]
        bonus = helper.make(original, "BONUS_ACCEPTED")
        bonus.update(acceptance="ACCEPT", acknowledges_txid=state[BANK]["MATURITY_REACHED"]["txid"])
        user_bonus = record(bonus, "f")
        state[USER]["BONUS_ACCEPTED"] = user_bonus
        state[BANK]["BONUS_ACCEPTED"] = record(dict(bonus, relay_ref=helper.proof(USER, user_bonus)), "1")
        completed = helper.make(original, "COMPLETED")
        completed["balance_representation"] = "Bank-side demonstration account record; no asset or fiat transfer"
        state[BANK]["COMPLETED"] = record(completed, "2")
        result = helper.complete("DEP001")
        self.assertEqual(result["txid"], "2" * 64)
        self.assertEqual(helper.clients[BANK].call.call_count, 0)

    def test_chain1_is_not_permitted(self):
        with self.assertRaisesRegex(ValueError, "never chain1"):
            credentials("chain1")

    def test_user_enters_amount_then_explicitly_accepts(self):
        helper, state = self.accepted_fixture()
        del state[USER]["DEPOSIT_ACCEPTED"]
        helper.publish = Mock()
        prompt = Mock(side_effect=["1000", "ACCEPT"])
        helper.accept("DEP001", prompt=prompt)
        self.assertEqual(prompt.call_count, 2)
        payload = helper.publish.call_args.args[1]
        self.assertEqual((payload["principal"], payload["bonus_percent"], payload["acceptance"]), (1000, 40, "ACCEPT"))
        self.assertEqual(helper.publish.call_args.args[0], USER)

    def test_user_amount_mismatch_never_publishes(self):
        helper, state = self.accepted_fixture()
        del state[USER]["DEPOSIT_ACCEPTED"]
        helper.publish = Mock()
        with self.assertRaisesRegex(ValueError, "match the bank offer"):
            helper.accept("DEP001", deposit_amount=2000, prompt=Mock(return_value="ACCEPT"))
        helper.publish.assert_not_called()

    def test_nonnumeric_interactive_amount_never_publishes(self):
        helper, state = self.accepted_fixture()
        del state[USER]["DEPOSIT_ACCEPTED"]
        helper.publish = Mock()
        with self.assertRaisesRegex(ValueError, "whole integer"):
            helper.accept("DEP001", prompt=Mock(return_value="not-an-amount"))
        helper.publish.assert_not_called()

    def test_user_can_decline_after_entering_amount(self):
        helper, state = self.accepted_fixture()
        del state[USER]["DEPOSIT_ACCEPTED"]
        helper.publish = Mock()
        with self.assertRaisesRegex(ValueError, "Not accepted"):
            helper.accept("DEP001", deposit_amount=1000, prompt=Mock(return_value="CANCEL"))
        helper.publish.assert_not_called()

    def test_bonus_acceptance_does_not_request_another_deposit(self):
        helper, state = self.accepted_fixture()
        helper.publish = Mock()
        prompt = Mock(return_value="ACCEPT")
        helper.accept("DEP001", bonus=True, prompt=prompt)
        self.assertEqual(prompt.call_count, 1)
        self.assertEqual(helper.publish.call_args.args[1]["bonus_amount"], 400)

    @patch("demo.save")
    @patch("demo.assert_filter_active")
    @patch("demo.time.sleep")
    @patch("demo.time.monotonic", side_effect=[0, 1, 2, 3, 4, 5, 6, 6])
    def test_six_month_timer_makes_forty_percent_bonus_ready_not_completed(self, clock, sleep, active, save):
        helper, state = self.accepted_fixture()
        del state[BANK]["MATURITY_REACHED"]
        del state[USER]["MATURITY_REACHED"]
        helper.publish = Mock()
        helper.mature("DEP001")
        self.assertEqual(sleep.call_count, 6)
        self.assertTrue(all(call.args == (1,) for call in sleep.call_args_list))
        payload = helper.publish.call_args.args[1]
        self.assertEqual(payload["event"], "MATURITY_REACHED")
        self.assertEqual(payload["status"], "BONUS_READY")
        self.assertEqual((payload["bonus_amount"], payload["final_amount"]), (400, 1400))
        self.assertEqual([tick["month"] for tick in payload["simulation"]["ticks"]], [1, 2, 3, 4, 5, 6])
        self.assertEqual(payload["simulation"]["elapsed_seconds"], 6)
        self.assertNotIn("COMPLETED", state[BANK])


if __name__ == "__main__":
    unittest.main()
