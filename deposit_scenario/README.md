# Bank / student deposit exam scenario: 40 percent only

Native Windows MultiChain 2.3.3, Python standard library and the existing PHP Web Demo. No new software, Solidity, assets or money transfers.

**GreenAddress / bank_events** is BANK; **k269012 / user_events** is USER. They are independent ledgers. `bank_filter.js` is the real MultiChain `bank_deposit_rules_40` stream filter, approved only for `bank_events`. The USER chain has no filter. `chain1` and Goffycoin are not used.

Current rule: **40% only**, maturity six demonstration months. For principal1000, bonus400 and final1400. The immutable old `bank_deposit_rules` (50/60%) is retained on-chain but must be inactive on bank_events. Its source is preserved in `bank_filter_legacy.js`; old DEP001 transactions and evidence are not rewritten. Use a NEW offer ID such as DEP040, not DEP001. A new filter does not amend the financial terms of historical offers.

The helper explicitly relays records, checks original terms/provenance and prior events, simulates time, and waits for confirmations. The V8 filter checks current-item structure/roles/arithmetic. It cannot read the other chain, prove that its JSON source assertions are genuine, remember historical acceptance, or sleep. An operator can bypass helper ordering by directly publishing a structurally valid record: this is an honest single-operator proof of concept, not a production banking contract or distributed exactly-once protocol.

Full preparation notes and screenshot checkpoints: `..\PREP.md`. Preserve existing data; do not rerun chain-creation commands for chains that already exist.

## Startup (CMD, separate windows)

All commands below run from the NEW location `C:\D\PhD\1\Blockchain\multichain-practical\multichain-web-demo`:

```cmd
..\multichain\multichaind.exe GreenAddress
..\multichain\multichaind.exe k269012
```

Run each in its own terminal, not sequentially in one blocked terminal. Keep the already-working PHP server running, or start it from this Web Demo directory using `php -S 127.0.0.1:8000`. Check `getinfo` before launching duplicate nodes. Windows does not implement `-daemon` as Linux does. Graceful stop: `..\multichain\multichain-cli.exe GreenAddress stop` (or `k269012 stop`). Never stop/reconfigure chain1 for this scenario.

## Filter lifecycle (one command at a time)

From the Web Demo root, stop on any unexpected error:

```cmd
python deposit_scenario\filter_tools.py compile
python deposit_scenario\filter_tools.py test
python deposit_scenario\filter_tools.py create
python deposit_scenario\filter_tools.py approve
python deposit_scenario\filter_tools.py retire-legacy
python deposit_scenario\filter_tools.py status
python deposit_scenario\filter_tools.py publish-tests
```

These are transparent wrappers for `teststreamfilter`, `createrawsendfrom ... sign`, `create streamfilter`, `approvefrom`, `liststreamfilters`/`liststreams`, and `publishfrom`. JSON and JavaScript are transported directly via JSON-RPC to avoid fragile Windows CLI quoting. Passwords are read from `%APPDATA%\MultiChain\<chain>\multichain.conf`, never printed. All endpoints are localhost, exact chain names/ports are checked, and the client refuses chain1.

Upgrade order matters: approve the new 40% filter FIRST, then `retire-legacy` disapproves only the known old filter for bank_events after comparing its archived code. There is no unfiltered interval. While both incompatible filters are active, no 40% workflow should be published; helper commands fail closed. Unknown filters are never automatically removed. Repeated create/approve/retire steps do not duplicate transactions. Capture the final listing showing new filter active on bank_events and old filter on no streams.

Native CLI examples (from Web Demo root):

```cmd
..\multichain\multichain-cli.exe GreenAddress getinfo
..\multichain\multichain-cli.exe GreenAddress liststreamfilters bank_deposit_rules_40 true
..\multichain\multichain-cli.exe GreenAddress getfiltercode bank_deposit_rules_40
..\multichain\multichain-cli.exe GreenAddress liststreams bank_events true
..\multichain\multichain-cli.exe k269012 liststreamfilters
..\multichain\multichain-cli.exe k269012 liststreams user_events true
```

`TEST40_VALID` is a separate synthetic validation fixture, not a real deposit completion. Invalid bonus/final/missing-field and old50/60% cases must return filter rejection and have zero items. New filter evidence is recorded in `results/bank_deposit_rules_40/`; original filter evidence is preserved. Do not mistake `compiled:true` for active: verify `liststreams bank_events true` includes ONLY `bank_deposit_rules_40` in `filters`.

## DEP040 workflow (explicit steps; no auto-acceptance)

Already completed steps are not repeated. `status` is always safe. Conflicting duplicates and duplicate BANK events fail closed. Identical USER acceptances are collapsed logically to the first record in chain order, and every ignored replay txid remains in the audit output/history. Use a NEW examiner-approved offer ID for another run; do not delete history.

```cmd
python deposit_scenario\demo.py offer DEP040 --principal 1000
python deposit_scenario\demo.py relay DEP040 --event DEPOSIT_OFFERED
python deposit_scenario\demo.py accept-deposit DEP040
python deposit_scenario\demo.py relay DEP040 --event DEPOSIT_ACCEPTED
python deposit_scenario\demo.py mature DEP040
python deposit_scenario\demo.py relay DEP040 --event MATURITY_REACHED
python deposit_scenario\demo.py accept-bonus DEP040
python deposit_scenario\demo.py relay DEP040 --event BONUS_ACCEPTED
python deposit_scenario\demo.py complete DEP040
python deposit_scenario\demo.py verify DEP040
```

For initial acceptance, the USER enters `1000` at the amount prompt, then explicitly types `ACCEPT`. Alternatively use `accept-deposit DEP040 --amount 1000` and type ACCEPT; do not use BOTH routes. The user's amount must match the original bank offer. To try another amount, change the bank's `--principal` and enter that same amount on USER under a new offer ID. Valid whole-unit principal values must be multiples of5 so the 40% bonus is an integer; e.g.2500 -> bonus1000 -> final3500.

At each `accept-*` prompt, the user must review the printed terms and type `ACCEPT`. Any other input cancels with no acceptance write. A maturity event requires banked initial acceptance. Completion requires a banked bonus acceptance whose referenced USER transaction/content is checked against the actual USER chain. The six-second timer prints Month1..Month6 and Maturity reached, and produces a timer evidence JSON. This is **application simulation**, not six months of blockchain time. Maturity makes the bonus AVAILABLE; final credit is not recorded until the user accepts that bonus and the acceptance is relayed back to BANK.

### Use the Web Demo instead for the two USER acceptances

Do EITHER GUI acceptance OR helper acceptance, never both for the same event.

1. Open `http://127.0.0.1:8000/?chain=k269012&page=publish`; heading must say `k269012 USER`.
2. To stream: `user_events`; keep **Publish as off-chain item unchecked** (the event data should be on-chain; the *relay program* is off-chain).
3. Initial acceptance: keys are `DEP040` and `DEPOSIT_ACCEPTED`, one per line. Generate the correct JSON with:

   ```cmd
   python deposit_scenario\demo.py acceptance-json DEP040
   ```

4. Paste output into **Or JSON**, leave upload and Or text empty. Read terms, click **Publish Item ONCE**, record txid and screenshot. This deliberate publish is the user's acceptance.
5. For bonus acceptance after receiving the maturity notification, use keys `DEP040` and `BONUS_ACCEPTED`; generate JSON with:

   ```cmd
   python deposit_scenario\demo.py acceptance-json DEP040 --bonus
   ```

6. Relay the acceptance using the corresponding `relay` command. The helper adds the source txid/output/hash reference on the destination ledger; the GUI user should not invent it.

Do not use the Web Demo's **Accept Offer** menu: that is for asset exchanges, not this deposit scenario. Do not refresh a successful POST page; navigate to Node/View Streams with a new GET instead.

Prefilled fields belong to ONE particular browser tab; they do not transfer to another browser/tab opened at the same URL. If your form is blank, do not click Publish Item. Generate/copy the JSON and enter both keys yourself, or use only the explicit CMD `accept-*` command and type ACCEPT. During rehearsal, an empty USER text item was accidentally published. It is preserved outside the DEP001 key, is not an acceptance, and is excluded from offer processing. The USER chain intentionally has no filter; the BANK filter would reject a non-JSON record.

## Inspect and reproduce

```cmd
python deposit_scenario\demo.py status DEP040
..\multichain\multichain-cli.exe GreenAddress liststreamkeyitems bank_events DEP040
..\multichain\multichain-cli.exe k269012 liststreamkeyitems user_events DEP040
```

These native listing commands default to ten items. The normal workflow has five BANK and four logical USER events; duplicate USER consent publications may add physical audit records. For larger histories, use explicit count/start. Verification queries up to10000 and refuses a truncated result. `demo.py verify` checks ordered logical events, original terms, hashes/source outputs, both acceptances, final values and bank-only filter activation. It reports identical consent replays separately. `complete` rerun is a no-op if the exact final event already exists. Direct concurrent/manual duplicate writes cannot be prevented atomically by this single-operator helper; conflicting duplicates stop it.

The NEW final bank-side record is principal1000 + bonus400 = final1400, statusCOMPLETED. Both50% and60% are now rejected. Historical DEP001 remains a50% record, not a new40% offer; consult its preserved verification JSON/raw transaction for the old result rather than rerunning its workflow under a new rule. Principal is a recorded demonstration deposit, not proof of fiat receipt. Use whole integer units; combinations yielding fractional bonuses are rejected rather than silently rounded. The USER chain records offer/acceptance/notification/bonus-acceptance, not a cross-chain token balance.

## Local tests and outputs

```cmd
python -m unittest discover -s deposit_scenario\tests -v
node deposit_scenario\tests\test_filter.cjs
python -m compileall -q deposit_scenario
```

Node is optional for local unit tests only; the actual filter runs in MultiChain V8, not Node. Python helper needs no pip packages. Evidence files under gitignored `results/` include filter compilation, native V8 tests, creation/approval/status, real publish rejections, `workflow.jsonl`, `<offer>_timer.json`, `<offer>_verification.json`. They contain public demo event data, no RPC credentials. No automated file logs can substitute for the examiner's required screenshots.
