# Bank / student deposit exam scenario

Native Windows MultiChain 2.3.3, Python standard library and the existing PHP Web Demo. No new software, Solidity, assets or money transfers.

**GreenAddress / bank_events** is BANK; **k269012 / user_events** is USER. They are independent ledgers. `bank_filter.js` is deployed as the real MultiChain `bank_deposit_rules` stream filter and approved only for `bank_events`. The USER chain has no filter. `chain1` and Goffycoin are not used.

The helper explicitly relays records, checks original terms/provenance and prior events, simulates time, and waits for confirmations. The V8 filter checks current-item structure/roles/arithmetic. It cannot read the other chain, prove that its JSON source assertions are genuine, remember historical acceptance, or sleep. An operator can bypass helper ordering by directly publishing a structurally valid record: this is an honest single-operator proof of concept, not a production banking contract or distributed exactly-once protocol.

Full preparation notes and screenshot checkpoints: `..\PREP.md`. Preserve existing data; do not rerun chain-creation commands for chains that already exist.

## Startup (CMD, separate windows)

From `C:\D\PhD\1\Blockchain\multichain-practical`:

```cmd
multichain\multichaind.exe GreenAddress
multichain\multichaind.exe k269012
```

Run each in its own terminal, not sequentially in one blocked terminal. Keep the already-working PHP server running, or start it from `multichain-web-demo` using `php -S 127.0.0.1:8000`. The two new nodes were initially started in the background; check `getinfo` before launching duplicates. Windows does not implement `-daemon` as Linux does. Graceful stop: `multichain\multichain-cli.exe GreenAddress stop` (or `k269012 stop`). Never stop/reconfigure chain1 for this scenario.

## Filter lifecycle (one command at a time)

From the practical root:

```cmd
python deposit_scenario\filter_tools.py compile
python deposit_scenario\filter_tools.py test
python deposit_scenario\filter_tools.py create
python deposit_scenario\filter_tools.py approve
python deposit_scenario\filter_tools.py status
python deposit_scenario\filter_tools.py publish-tests
```

These are transparent wrappers for `teststreamfilter`, `createrawsendfrom ... sign`, `create streamfilter`, `approvefrom`, `liststreamfilters`/`liststreams`, and `publishfrom`. JSON and JavaScript are transported directly via JSON-RPC to avoid fragile Windows CLI quoting. Passwords are read from `%APPDATA%\MultiChain\<chain>\multichain.conf`, never printed. All endpoints are localhost, exact chain names/ports are checked, and the client refuses chain1.

Native CLI examples (from practical root):

```cmd
multichain\multichain-cli.exe GreenAddress getinfo
multichain\multichain-cli.exe GreenAddress liststreamfilters bank_deposit_rules true
multichain\multichain-cli.exe GreenAddress getfiltercode bank_deposit_rules
multichain\multichain-cli.exe GreenAddress liststreams bank_events true
multichain\multichain-cli.exe k269012 liststreamfilters
multichain\multichain-cli.exe k269012 liststreams user_events true
```

`TEST_VALID` is a separate synthetic validation fixture, not a real DEP001 completion. Invalid bonus/final/missing-field cases must return filter rejection and have zero items. Test outcomes are recorded in `results/`. Do not mistake `compiled:true` for active: verify `liststreams bank_events true` includes `bank_deposit_rules` in `filters`.

## DEP001 workflow (explicit steps; no auto-acceptance)

Already completed steps are not repeated. `status` is always safe. Conflicting duplicates and duplicate BANK events fail closed. Identical USER acceptances are collapsed logically to the first record in chain order, and every ignored replay txid remains in the audit output/history. Use a NEW examiner-approved offer ID for another run; do not delete history.

```cmd
python deposit_scenario\demo.py offer DEP001 --principal 1000 --bonus-percent 50
python deposit_scenario\demo.py relay DEP001 --event DEPOSIT_OFFERED
python deposit_scenario\demo.py accept-deposit DEP001
python deposit_scenario\demo.py relay DEP001 --event DEPOSIT_ACCEPTED
python deposit_scenario\demo.py mature DEP001
python deposit_scenario\demo.py relay DEP001 --event MATURITY_REACHED
python deposit_scenario\demo.py accept-bonus DEP001
python deposit_scenario\demo.py relay DEP001 --event BONUS_ACCEPTED
python deposit_scenario\demo.py complete DEP001
python deposit_scenario\demo.py verify DEP001
```

At each `accept-*` prompt, the user must review the printed terms and type `ACCEPT`. Any other input cancels with no acceptance write. A maturity event requires banked initial acceptance. Completion requires a banked bonus acceptance whose referenced USER transaction/content is checked against the actual USER chain. The six-second timer prints Month1..Month6 and Maturity reached, and produces a timer evidence JSON. This is **application simulation**, not six months of blockchain time.

### Use the Web Demo instead for the two USER acceptances

Do EITHER GUI acceptance OR helper acceptance, never both for the same event.

1. Open `http://127.0.0.1:8000/?chain=k269012&page=publish`; heading must say `k269012 USER`.
2. To stream: `user_events`; keep **Publish as off-chain item unchecked** (the event data should be on-chain; the *relay program* is off-chain).
3. Initial acceptance: keys are `DEP001` and `DEPOSIT_ACCEPTED`, one per line. Generate the correct JSON with:

   ```cmd
   python deposit_scenario\demo.py acceptance-json DEP001
   ```

4. Paste output into **Or JSON**, leave upload and Or text empty. Read terms, click **Publish Item ONCE**, record txid and screenshot. This deliberate publish is the user's acceptance.
5. For bonus acceptance after receiving the maturity notification, use keys `DEP001` and `BONUS_ACCEPTED`; generate JSON with:

   ```cmd
   python deposit_scenario\demo.py acceptance-json DEP001 --bonus
   ```

6. Relay the acceptance using the corresponding `relay` command. The helper adds the source txid/output/hash reference on the destination ledger; the GUI user should not invent it.

Do not use the Web Demo's **Accept Offer** menu: that is for asset exchanges, not this deposit scenario. Do not refresh a successful POST page; navigate to Node/View Streams with a new GET instead.

Prefilled fields belong to ONE particular browser tab; they do not transfer to another browser/tab opened at the same URL. If your form is blank, do not click Publish Item. Generate/copy the JSON and enter both keys yourself, or use only the explicit CMD `accept-*` command and type ACCEPT. During rehearsal, an empty USER text item was accidentally published. It is preserved outside the DEP001 key, is not an acceptance, and is excluded from offer processing. The USER chain intentionally has no filter; the BANK filter would reject a non-JSON record.

## Inspect and reproduce

```cmd
python deposit_scenario\demo.py status DEP001
multichain\multichain-cli.exe GreenAddress liststreamkeyitems bank_events DEP001
multichain\multichain-cli.exe k269012 liststreamkeyitems user_events DEP001
```

These native listing commands default to ten items. The normal workflow has five BANK and four logical USER events; duplicate USER consent publications may add physical audit records. For larger histories, use explicit count/start. Verification queries up to10000 and refuses a truncated result. `demo.py verify` checks ordered logical events, original terms, hashes/source outputs, both acceptances, final values and bank-only filter activation. It reports identical consent replays separately. `complete` rerun is a no-op if the exact final event already exists. Direct concurrent/manual duplicate writes cannot be prevented atomically by this single-operator helper; conflicting duplicates stop it.

The final bank-side record is principal1000 + bonus500 = final1500, statusCOMPLETED. At60%, it would be bonus600/final1600. Principal is a recorded demonstration deposit, not proof of fiat receipt. Use whole integer units; combinations yielding fractional bonuses are rejected rather than silently rounded. The USER chain records offer/acceptance/notification/bonus-acceptance, not a cross-chain token balance.

## Local tests and outputs

```cmd
python -m unittest discover -s deposit_scenario\tests -v
node deposit_scenario\tests\test_filter.cjs
python -m compileall -q deposit_scenario
```

Node is optional for local unit tests only; the actual filter runs in MultiChain V8, not Node. Python helper needs no pip packages. Evidence files under gitignored `results/` include filter compilation, native V8 tests, creation/approval/status, real publish rejections, `workflow.jsonl`, `<offer>_timer.json`, `<offer>_verification.json`. They contain public demo event data, no RPC credentials. No automated file logs can substitute for the examiner's required screenshots.
