"""One explicit real-MultiChain filter lifecycle step per command; no chain creation."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time
from rpc_client import BANK, USER, STREAMS, FILTER, LEGACY_FILTER, RPC, RPCError

HERE = Path(__file__).resolve().parent


def save(name, value, namespace=None):
    directory = HERE / "results"
    if namespace is not None:
        directory = directory / namespace
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def save_filter(name, value):
    # Keep the old 50/60-percent rehearsal evidence intact.
    save(name, value, namespace=FILTER)


def wait_confirmed(rpc, txid):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        transaction = rpc.call("getrawtransaction", txid, 1)
        if transaction.get("confirmations", 0) >= 1:
            return transaction["confirmations"]
        time.sleep(1)
    raise RuntimeError("Transaction {} submitted but not yet confirmed. Inspect it; do NOT blindly resubmit.".format(txid))


def active_names(rpc):
    return {item.get("name") for item in
            rpc.call("liststreams", STREAMS[BANK], True)[0].get("filters", [])}


def active(rpc):
    return FILTER in active_names(rpc)


def cases():
    valid = json.loads((HERE / "examples" / "valid.json").read_text(encoding="utf-8"))
    bad_bonus = copy.deepcopy(valid)
    bad_bonus.update(offer_id="TEST40_BAD_BONUS", bonus_amount=300, final_amount=1300)
    bad_final = copy.deepcopy(valid)
    bad_final.update(offer_id="TEST40_BAD_FINAL", final_amount=1300)
    missing = copy.deepcopy(valid)
    missing["offer_id"] = "TEST40_MISSING"
    del missing["principal"]
    old_fifty = dict(valid, offer_id="TEST40_RATE_50", bonus_percent=50, bonus_amount=500, final_amount=1500)
    old_sixty = dict(valid, offer_id="TEST40_RATE_60", bonus_percent=60, bonus_amount=600, final_amount=1600)
    return [("valid", valid, None), ("invalid_bonus", bad_bonus, "Incorrect bonus amount"),
            ("invalid_final", bad_final, "Incorrect final amount"),
            ("missing_field", missing, "Missing required field: principal"),
            ("rate_50_rejected", old_fifty, "bonus_percent must be 40"),
            ("rate_60_rejected", old_sixty, "bonus_percent must be 40")]


def assert_filter_active(rpc, allow_legacy=False):
    names = active_names(rpc)
    if FILTER not in names:
        raise ValueError("Bank filter is not active on bank_events. Stop; approve and confirm it first.")
    code = (HERE / "bank_filter.js").read_text(encoding="utf-8")
    if rpc.call("getfiltercode", FILTER) != code:
        raise ValueError("Active deployed filter differs from local bank_filter.js; stop and inspect.")
    unexpected = names - ({FILTER, LEGACY_FILTER} if allow_legacy else {FILTER})
    if unexpected:
        raise ValueError("Other active bank filters: {}. Retire the known legacy rule before publishing; do not remove unknown filters blindly.".format(sorted(unexpected)))


def retire_legacy(bank, address):
    # Activate the replacement FIRST: there is never an unfiltered interval.
    assert_filter_active(bank, allow_legacy=True)
    if LEGACY_FILTER not in active_names(bank):
        assert_filter_active(bank)
        print("Legacy filter already inactive; no duplicate disapproval sent.")
        return {"retired": False, "already_inactive": True}
    legacy_code = (HERE / "bank_filter_legacy.js").read_text(encoding="utf-8")
    if bank.call("getfiltercode", LEGACY_FILTER) != legacy_code:
        raise ValueError("Legacy deployed code differs from the archived source; refusing disapproval.")
    txid = bank.call("approvefrom", address, LEGACY_FILTER, {"for": STREAMS[BANK], "approve": False})
    print("Legacy filter disapproval txid: " + txid, flush=True)
    confirmations = wait_confirmed(bank, txid)
    assert_filter_active(bank)
    report = {"retired": True, "txid": txid, "confirmations": confirmations,
              "chain": BANK, "stream": STREAMS[BANK], "retired_filter": LEGACY_FILTER,
              "active_filter": FILTER, "old_filter_and_history_deleted": False,
              "legacy_code_sha256": hashlib.sha256(legacy_code.encode("utf-8")).hexdigest()}
    save_filter("filter_upgrade.json", report)
    print("READY: only the 40-percent filter is active on GreenAddress/bank_events")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=["compile", "test", "create", "approve", "retire-legacy", "status", "publish-tests"])
    args = parser.parse_args()
    bank = RPC(BANK)
    address = bank.call("liststreams", STREAMS[BANK], True)[0]["creators"][0]
    code = (HERE / "bank_filter.js").read_text(encoding="utf-8")
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    print("Chain: {} | Stream: {} | Filter: {}".format(BANK, STREAMS[BANK], FILTER), flush=True)
    if args.step == "compile":
        result = bank.call("teststreamfilter", {}, code)
        save_filter("filter_compile.json", result)
        print(json.dumps(result, indent=2))
        if not result.get("compiled"):
            raise ValueError("Filter failed to compile; stop this stage.")
    elif args.step == "test":
        reports = []
        for name, payload, expected in cases():
            signed = bank.call("createrawsendfrom", address, {}, [{"for": STREAMS[BANK],
                "keys": [payload["offer_id"], payload["event"]], "data": {"json": payload}}], "sign")
            result = bank.call("teststreamfilter", {}, code, signed["hex"])
            correct = bool(result.get("compiled")) and (bool(result.get("passed")) == (expected is None))
            if expected:
                correct = correct and expected in (result.get("reason") or "")
            print("{}: passed={} reason={}".format(name, result.get("passed"), result.get("reason")), flush=True)
            reports.append({"case": name, "expected_error": expected, "correct": correct, "result": result})
            if not correct:
                save_filter("filter_test_failure.json", {"filter_sha256": code_hash, "tests": reports})
                raise ValueError("Unexpected real-V8 test result; stop before deployment.")
        save_filter("filter_tests.json", {"filter_sha256": code_hash, "tests": reports, "all_correct": True,
                                  "note": "Signed test transactions were NOT broadcast."})
    elif args.step == "create":
        report = json.loads((HERE / "results" / FILTER / "filter_tests.json").read_text(encoding="utf-8"))
        if not report.get("all_correct") or report.get("filter_sha256") != code_hash:
            raise ValueError("Test the exact code before creating it.")
        existing = [f for f in bank.call("liststreamfilters", "*", True) if f.get("name") == FILTER]
        if existing:
            if bank.call("getfiltercode", FILTER) != code:
                raise ValueError("Filter already exists with different code. Never replace it blindly.")
            print("Already created; no duplicate transaction sent.")
            return
        txid = bank.call("create", "streamfilter", FILTER, {}, code)
        print("Filter creation txid: " + txid, flush=True)
        confirmations = wait_confirmed(bank, txid)
        save_filter("filter_creation.json", {"txid": txid, "confirmations": confirmations,
                                       "filter_sha256": code_hash})
        print(json.dumps(bank.call("liststreamfilters", FILTER, True), indent=2))
    elif args.step == "approve":
        if active(bank):
            assert_filter_active(bank, allow_legacy=True)
            print("Already active on bank_events; no duplicate approval sent.")
            if LEGACY_FILTER in active_names(bank):
                print("Next run retire-legacy. Both rate rules currently block new 40-percent items.")
            return
        if bank.call("getfiltercode", FILTER) != code:
            raise ValueError("Deployed code mismatch; refusing approval.")
        txid = bank.call("approvefrom", address, FILTER, {"for": STREAMS[BANK], "approve": True})
        print("Approval txid: " + txid, flush=True)
        confirmations = wait_confirmed(bank, txid)
        assert_filter_active(bank, allow_legacy=True)
        save_filter("filter_approval.json", {"txid": txid, "confirmations": confirmations,
                                       "chain": BANK, "stream": STREAMS[BANK]})
        print("40-percent filter approved on bank_events. Run retire-legacy before publishing if the old filter is still active.")
    elif args.step == "retire-legacy":
        retire_legacy(bank, address)
    elif args.step == "status":
        result = {"bank_filters": bank.call("liststreamfilters", "*", True),
                  "bank_stream": bank.call("liststreams", STREAMS[BANK], True),
                  "user_filters": RPC(USER).call("liststreamfilters", "*", True)}
        save_filter("filter_status.json", result)
        print(json.dumps(result, indent=2))
        assert_filter_active(bank)
        if result["user_filters"]:
            raise ValueError("Unexpected filter on USER chain; inspect, do not remove automatically.")
    elif args.step == "publish-tests":
        assert_filter_active(bank)
        report = []
        for name, payload, expected in cases():
            previous = bank.call("liststreamkeyitems", STREAMS[BANK], payload["offer_id"], False, 100, 0)
            if not expected and previous:
                if len(previous) != 1 or previous[0].get("data", {}).get("json") != payload:
                    raise ValueError("Existing valid-test fixture differs; inspect instead of reusing it.")
                print("valid: already published, no duplicate sent.")
                report.append({"case": name, "accepted": True, "txid": previous[0]["txid"], "already_present": True})
                continue
            try:
                txid = bank.call("publishfrom", address, STREAMS[BANK],
                                [payload["offer_id"], payload["event"]], {"json": payload})
            except RPCError as error:
                if expected is None or expected not in str(error):
                    raise
                remaining = bank.call("liststreamkeyitems", STREAMS[BANK], payload["offer_id"], False, 100, 0)
                if remaining:
                    raise ValueError("Rejected-test key unexpectedly has stream records; inspect it.")
                print("{}: REJECTED by real API: {}".format(name, error), flush=True)
                report.append({"case": name, "accepted": False, "error": str(error), "stream_items": 0})
            else:
                if expected:
                    raise ValueError("Invalid event unexpectedly published as {}. Stop immediately.".format(txid))
                print("valid: ACCEPTED, txid=" + txid, flush=True)
                confirmations = wait_confirmed(bank, txid)
                report.append({"case": name, "accepted": True, "txid": txid, "confirmations": confirmations})
        save_filter("filter_publish_tests.json", {"tests": report, "all_expected_outcomes": True,
             "note": "TEST40_VALID is an isolated validation fixture, NOT a deposit workflow."})


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError) as error:
        raise SystemExit(str(error))
