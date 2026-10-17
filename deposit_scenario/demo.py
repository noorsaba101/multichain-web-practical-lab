"""Explicit exam steps: offer, relay, accept-deposit, mature, accept-bonus, complete, verify.

Single-operator demonstration. Stream queries prevent sequential reprocessing, not
an atomic distributed exactly-once protocol. All money is an audit/account record.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import time
from rpc_client import BANK, USER, STREAMS, FILTER, BONUS_PERCENT, RPC
from filter_tools import assert_filter_active, wait_confirmed, save

HERE = Path(__file__).resolve().parent
STATUSES = {"DEPOSIT_OFFERED": "OFFERED", "DEPOSIT_ACCEPTED": "ACCEPTED",
            "MATURITY_REACHED": "BONUS_READY", "BONUS_ACCEPTED": "BONUS_ACCEPTED", "COMPLETED": "COMPLETED"}
TERMS = ("schema_version", "offer_id", "user_id", "principal", "bonus_percent", "maturity_months")
BANK_SEQUENCE = list(STATUSES)
USER_SEQUENCE = BANK_SEQUENCE[:-1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()


def amounts(principal, percent):
    if type(principal) is not int or not 0 < principal <= 1000000000:
        raise ValueError("Principal must be an integer in 1..1000000000.")
    if type(percent) is not int or percent != BONUS_PERCENT:
        raise ValueError("Bonus percent must be 40 only. Use a new offer; historical terms are not changed.")
    if principal * percent % 100:
        raise ValueError("Use whole demonstration units with an integer bonus.")
    bonus = principal * percent // 100
    return bonus, principal + bonus


def body(record):
    value = record.get("data", {}).get("json") if isinstance(record.get("data"), dict) else None
    if record.get("available") is False or not isinstance(value, dict):
        raise ValueError("Unavailable/non-JSON stream record; fail closed and inspect the filter error.")
    return value


def index_records(records, offer_id, allow_identical_acceptances=False):
    events = {}
    for record in records:
        value = body(record)
        if value.get("offer_id") != offer_id or value.get("event") not in STATUSES:
            raise ValueError("Unexpected record under this offer key; inspect it before continuing.")
        event = value["event"]
        if event in events:
            if (allow_identical_acceptances and event in ("DEPOSIT_ACCEPTED", "BONUS_ACCEPTED")
                    and body(events[event]) == value):
                # Two deliberate UI/CLI publishes can record the same consent.
                # Keep the first in chain order; preserve and report all replay txids.
                canonical = copy.deepcopy(events[event])
                canonical.setdefault("identical_replay_txids", []).append(record["txid"])
                events[event] = canonical
                continue
            raise ValueError("Duplicate {} for {} already exists. Stop; do not credit again.".format(event, offer_id))
        events[event] = record
    return events


class Demo:
    def __init__(self, clients=None):
        self.clients = clients or {BANK: RPC(BANK), USER: RPC(USER)}

    def events(self, chain, offer):
        records = self.clients[chain].call("liststreamkeyitems", STREAMS[chain], offer, False, 10000, 0)
        if len(records) >= 10000:
            raise ValueError("Query limit reached; refusing an incomplete duplicate check.")
        return index_records(records, offer, allow_identical_acceptances=chain == USER)

    def require(self, chain, offer, event):
        record = self.events(chain, offer).get(event)
        if record is None:
            raise ValueError("Missing {} on {}/{}; complete/relay that step first.".format(event, chain, STREAMS[chain]))
        return record

    def original(self, offer):
        return self.require(BANK, offer, "DEPOSIT_OFFERED")

    def check_terms(self, record, original):
        value, base = body(record), body(original)
        if any(value.get(key) != base[key] for key in TERMS):
            raise ValueError("Terms differ from the original bank offer.")
        bonus, final = amounts(base["principal"], base["bonus_percent"])
        if "bonus_amount" in value and (value["bonus_amount"], value.get("final_amount")) != (bonus, final):
            raise ValueError("Incorrect stored bonus/final amount.")

    def proof(self, chain, record):
        # MultiChain 2.3.3 stream retrieval omits vout. Resolve it from the actual
        # decoded transaction, never assume output zero or invent a reference.
        vout = record.get("vout")
        if vout is None:
            transaction = self.clients[chain].call("getrawtransaction", record["txid"], 1)
            matches = []
            for output in transaction["vout"]:
                for item in output.get("items", []):
                    if item.get("name") == STREAMS[chain] and item.get("data", {}).get("json") == body(record):
                        matches.append(output["n"])
            if len(matches) != 1:
                raise ValueError("Cannot unambiguously locate source stream output; stop relay.")
            vout = matches[0]
        return {"chain": chain, "stream": STREAMS[chain], "txid": record["txid"],
                "vout": vout, "payload_sha256": digest(body(record))}

    def verify_relay(self, copy_record, original_record, original_chain):
        expected = copy.deepcopy(body(original_record))
        expected["relay_ref"] = self.proof(original_chain, original_record)
        if body(copy_record) != expected:
            raise ValueError("Relay content/reference does not match the actual source-chain record.")

    def make(self, original, event):
        value = {key: body(original)[key] for key in TERMS}
        user_event = event in ("DEPOSIT_ACCEPTED", "BONUS_ACCEPTED")
        value.update(event=event, status=STATUSES[event], actor_role="USER" if user_event else "BANK",
                     source_chain=USER if user_event else BANK,
                     destination_chain=BANK if user_event or event == "COMPLETED" else USER)
        if event in ("MATURITY_REACHED", "BONUS_ACCEPTED", "COMPLETED"):
            value["bonus_amount"], value["final_amount"] = amounts(value["principal"], value["bonus_percent"])
        return value

    def publish(self, chain, value):
        previous = self.events(chain, value["offer_id"]).get(value["event"])
        if previous:
            if body(previous) != value:
                raise ValueError("This event already exists with different data. No transaction sent.")
            print("ALREADY HANDLED {} on {}: {}. No transaction sent.".format(value["event"], chain, previous["txid"]))
            return previous
        rpc = self.clients[chain]
        if chain == BANK:
            assert_filter_active(rpc)
        stream = STREAMS[chain]
        publisher = rpc.call("liststreams", stream, True)[0]["creators"][0]
        print("Publishing {} -> {}/{} (real publishfrom RPC)".format(value["event"], chain, stream), flush=True)
        txid = rpc.call("publishfrom", publisher, stream, [value["offer_id"], value["event"]], {"json": value})
        print("Transaction: " + txid, flush=True)
        confirmations = wait_confirmed(rpc, txid)
        record = self.require(chain, value["offer_id"], value["event"])
        receipt = {"chain": chain, "stream": stream, "txid": txid, "confirmations": confirmations, "payload": value}
        (HERE / "results").mkdir(exist_ok=True)
        with (HERE / "results" / "workflow.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt, allow_nan=False) + "\n")
        print(json.dumps(receipt, indent=2), flush=True)
        return record

    def offer(self, offer, principal=1000, percent=BONUS_PERCENT):
        amounts(principal, percent)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", offer):
            raise ValueError("Invalid offer_id.")
        value = dict(schema_version=1, offer_id=offer, user_id=USER, principal=principal,
                     bonus_percent=percent, maturity_months=6)
        value.update(event="DEPOSIT_OFFERED", status="OFFERED", actor_role="BANK",
                     source_chain=BANK, destination_chain=USER)
        return self.publish(BANK, value)

    def relay(self, offer, event):
        source, target = (BANK, USER) if event in ("DEPOSIT_OFFERED", "MATURITY_REACHED") else (USER, BANK)
        original = self.original(offer)
        source_record = self.require(source, offer, event)
        wait_confirmed(self.clients[source], source_record["txid"])
        self.check_terms(source_record, original)
        if event in ("DEPOSIT_ACCEPTED", "BONUS_ACCEPTED"):
            if body(source_record).get("acceptance") != "ACCEPT":
                raise ValueError("User event lacks explicit ACCEPT.")
            notice_event = "DEPOSIT_OFFERED" if event == "DEPOSIT_ACCEPTED" else "MATURITY_REACHED"
            bank_notice = self.require(BANK, offer, notice_event)
            user_notice = self.require(USER, offer, notice_event)
            self.verify_relay(user_notice, bank_notice, BANK)
            if body(source_record).get("acknowledges_txid") != bank_notice["txid"]:
                raise ValueError("Acceptance does not reference the correct bank notice.")
        value = copy.deepcopy(body(source_record))
        value["relay_ref"] = self.proof(source, source_record)
        print("OFF-CHAIN RELAY: {} -> {}; independent ledgers, not automatic messaging.".format(source, target))
        return self.publish(target, value)

    def acceptance_payload(self, offer, bonus=False):
        event = "BONUS_ACCEPTED" if bonus else "DEPOSIT_ACCEPTED"
        original = self.original(offer)
        notice_event = "MATURITY_REACHED" if bonus else "DEPOSIT_OFFERED"
        bank_notice = self.require(BANK, offer, notice_event)
        user_notice = self.require(USER, offer, notice_event)
        self.check_terms(bank_notice, original)
        self.verify_relay(user_notice, bank_notice, BANK)
        value = self.make(original, event)
        value.update(acceptance="ACCEPT", acknowledges_txid=bank_notice["txid"])
        return value

    def accept(self, offer, bonus=False, prompt=input, deposit_amount=None):
        event = "BONUS_ACCEPTED" if bonus else "DEPOSIT_ACCEPTED"
        existing = self.events(USER, offer).get(event)
        if existing:
            print("Already accepted: {}. No duplicate transaction sent.".format(existing["txid"]))
            return existing
        value = self.acceptance_payload(offer, bonus)
        original = self.original(offer)
        p = body(original)
        reward, final = amounts(p["principal"], p["bonus_percent"])
        print("Offer {} | user {} | principal {} | bonus {}% = {} | final {} | maturity 6 demo months".format(
            offer, USER, p["principal"], p["bonus_percent"], reward, final), flush=True)
        if not bonus:
            if deposit_amount is None:
                try:
                    deposit_amount = int(prompt("Enter your deposit amount in whole demonstration units: ").strip())
                except (ValueError, TypeError):
                    raise ValueError("Deposit amount must be a whole integer. No acceptance event written.") from None
            if type(deposit_amount) is not int or deposit_amount != p["principal"]:
                raise ValueError("Deposit amount must match the bank offer principal {}. No acceptance event written.".format(p["principal"]))
        if prompt("Type ACCEPT to {} (anything else cancels): ".format("accept the maturity bonus" if bonus else "accept these initial terms")).strip() != "ACCEPT":
            raise ValueError("Not accepted. No acceptance event written.")
        return self.publish(USER, value)

    def require_banked_acceptance(self, offer, event):
        bank_record = self.require(BANK, offer, event)
        user_record = self.require(USER, offer, event)
        self.check_terms(user_record, self.original(offer))
        self.verify_relay(bank_record, user_record, USER)
        if body(user_record).get("acceptance") != "ACCEPT":
            raise ValueError("Explicit user acceptance missing.")
        notice = self.require(BANK, offer, "DEPOSIT_OFFERED" if event == "DEPOSIT_ACCEPTED" else "MATURITY_REACHED")
        if body(user_record).get("acknowledges_txid") != notice["txid"]:
            raise ValueError("Wrong notice acknowledged.")
        self.verify_relay(self.require(USER, offer, body(notice)["event"]), notice, BANK)
        return bank_record

    def mature(self, offer):
        original = self.original(offer)
        self.require_banked_acceptance(offer, "DEPOSIT_ACCEPTED")
        existing = self.events(BANK, offer).get("MATURITY_REACHED")
        if existing:
            print("Maturity already recorded; timer not repeated: " + existing["txid"])
            return existing
        assert_filter_active(self.clients[BANK])
        print("DEMO ONLY: 1 second represents 1 month. This is NOT MultiChain time.", flush=True)
        started = time.monotonic()
        ticks = []
        for month in range(1, 7):
            time.sleep(1)
            print("Month {}".format(month), flush=True)
            ticks.append({"month": month, "elapsed_seconds": round(time.monotonic() - started, 3)})
        print("Maturity reached", flush=True)
        simulation = {"demo_only": True, "seconds_per_month": 1, "months": 6,
                      "elapsed_seconds": round(time.monotonic() - started, 3), "ticks": ticks}
        save(offer + "_timer.json", simulation)
        value = self.make(original, "MATURITY_REACHED")
        value["simulation"] = simulation
        return self.publish(BANK, value)

    def complete(self, offer):
        original = self.original(offer)
        self.require_banked_acceptance(offer, "DEPOSIT_ACCEPTED")
        self.check_terms(self.require(BANK, offer, "MATURITY_REACHED"), original)
        self.require_banked_acceptance(offer, "BONUS_ACCEPTED")
        value = self.make(original, "COMPLETED")
        value["balance_representation"] = "Bank-side demonstration account record; no asset or fiat transfer"
        return self.publish(BANK, value)

    def status(self, offer, verify=False):
        bank, user = self.events(BANK, offer), self.events(USER, offer)
        report = {"offer_id": offer, "bank": {key: r["txid"] for key, r in bank.items()},
                  "user": {key: r["txid"] for key, r in user.items()},
                  "identical_user_acceptance_replays": {
                      event: {"canonical_txid": r["txid"], "ignored_replay_txids": r["identical_replay_txids"]}
                      for event, r in user.items() if r.get("identical_replay_txids")},
                  "final_bank_record": body(bank["COMPLETED"]) if "COMPLETED" in bank else None}
        if verify:
            if list(bank) != BANK_SEQUENCE or list(user) != USER_SEQUENCE:
                raise ValueError("Expected five ordered bank events and four ordered logical user events.")
            original = self.original(offer)
            for record in list(bank.values()) + list(user.values()):
                if record.get("confirmations", 0) < 1:
                    raise ValueError("An event is not yet confirmed; wait before claiming success.")
                self.check_terms(record, original)
            self.verify_relay(user["DEPOSIT_OFFERED"], bank["DEPOSIT_OFFERED"], BANK)
            self.verify_relay(user["MATURITY_REACHED"], bank["MATURITY_REACHED"], BANK)
            self.require_banked_acceptance(offer, "DEPOSIT_ACCEPTED")
            self.require_banked_acceptance(offer, "BONUS_ACCEPTED")
            expected = self.make(original, "COMPLETED")
            expected["balance_representation"] = "Bank-side demonstration account record; no asset or fiat transfer"
            if body(bank["COMPLETED"]) != expected:
                raise ValueError("Final record differs from the accepted terms.")
            assert_filter_active(self.clients[BANK])
            if self.clients[USER].call("liststreamfilters", "*", True):
                raise ValueError("Unexpected user-chain filter.")
            replay_count = sum(len(r.get("identical_replay_txids", [])) for r in user.values())
            report.update(verified=True, bank_duplicate_events=0, bank_offer_records=5, logical_user_events=4,
                          user_offer_records=4 + replay_count, ignored_identical_acceptance_replays=replay_count,
                          total_bank_stream_items=self.clients[BANK].call("liststreams", STREAMS[BANK], True)[0]["items"],
                          total_user_stream_items=self.clients[USER].call("liststreams", STREAMS[USER], True)[0]["items"],
                          chains={"bank": BANK, "user": USER}, filter_name=FILTER,
                          filter_code_sha256=hashlib.sha256((HERE / "bank_filter.js").read_text(encoding="utf-8").encode("utf-8")).hexdigest(),
                          filter_on_bank_only=True, cross_chain_transport="explicit off-chain helper relay")
            save(offer + "_verification.json", report)
        print(json.dumps(report, indent=2), flush=True)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=["offer", "relay", "accept-deposit", "mature", "accept-bonus", "acceptance-json", "complete", "status", "verify"])
    parser.add_argument("offer_id", nargs="?", default="DEP040")
    parser.add_argument("--event", choices=USER_SEQUENCE)
    parser.add_argument("--principal", type=int, default=1000)
    parser.add_argument("--bonus-percent", type=int, choices=[BONUS_PERCENT], default=BONUS_PERCENT)
    parser.add_argument("--amount", type=int, help="For accept-deposit: user's amount; must match the bank offer. Omit to enter it interactively.")
    parser.add_argument("--bonus", action="store_true", help="For acceptance-json: prepare maturity-bonus acceptance instead of initial acceptance")
    args = parser.parse_args()
    if args.amount is not None and args.step != "accept-deposit":
        parser.error("--amount is only for accept-deposit; use --principal when preparing the bank offer")
    demo = Demo()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", args.offer_id):
        raise ValueError("Invalid offer_id.")
    if args.step == "offer":
        demo.offer(args.offer_id, args.principal, args.bonus_percent)
    elif args.step == "relay":
        if not args.event:
            parser.error("relay requires --event")
        demo.relay(args.offer_id, args.event)
    elif args.step.startswith("accept-"):
        demo.accept(args.offer_id, bonus=args.step == "accept-bonus", deposit_amount=args.amount)
    elif args.step == "acceptance-json":
        event = "BONUS_ACCEPTED" if args.bonus else "DEPOSIT_ACCEPTED"
        if event in demo.events(USER, args.offer_id):
            raise ValueError("This acceptance already exists; do not publish it again.")
        print(json.dumps(demo.acceptance_payload(args.offer_id, args.bonus), indent=2))
    elif args.step in ("status", "verify"):
        demo.status(args.offer_id, verify=args.step == "verify")
    else:
        getattr(demo, args.step)(args.offer_id)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, EOFError) as error:
        raise SystemExit(str(error))
