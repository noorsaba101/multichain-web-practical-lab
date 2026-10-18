# Bank/student deposit walkthrough

Use native Windows CMD from the repository root. Prepare the nodes, streams and private configuration using [Windows setup](../docs/SETUP.md). The helper needs Python's standard library only; the deployed JavaScript runs in MultiChain V8.

## Business rules and responsibilities

- BANK: `GreenAddress/bank_events`. USER: `k269012/user_events`. They are independent ledgers, linked only by the explicit off-chain relay.
- Current filter: `bank_deposit_rules_40`, active only on `bank_events`. The USER chain has no filter.
- Principal must be a positive integer no greater than 1,000,000,000. The bonus is **40% only**, and maturity is six demonstration months. Use multiples of 5 for whole-unit bonuses; fractional bonuses are rejected, not rounded.
- For principal 1,000, bonus = 400 and final amount = 1,400. A different amount must be set in the original bank offer and matched by the USER. Accepted terms are immutable for that offer ID.
- The filter checks JSON structure, required fields, schema version, offer ID/key, user ID, event/status, role/direction, relay reference shape and arithmetic.
- The helper verifies actual source transaction references, terms, acceptance history, event ordering and sequential duplicate processing. It runs the timer and transports events; the filter does not sleep, contact the other chain or remember prior events.
- A direct structurally valid publication can bypass the helper's historical workflow. This is a single-operator practical, not a production banking contract or distributed exactly-once protocol. No fiat or token transfer is performed.

| Event | Required status | Actor/source -> destination |
| --- | --- | --- |
| DEPOSIT_OFFERED | OFFERED | BANK / GreenAddress -> k269012 |
| DEPOSIT_ACCEPTED | ACCEPTED | USER / k269012 -> GreenAddress |
| MATURITY_REACHED | BONUS_READY | BANK / GreenAddress -> k269012 |
| BONUS_ACCEPTED | BONUS_ACCEPTED | USER / k269012 -> GreenAddress |
| COMPLETED | COMPLETED | BANK / GreenAddress -> GreenAddress |

## 1. Test, deploy and activate the filter

Run each command separately and stop on unexpected errors:

```cmd
python deposit_scenario\filter_tools.py compile
python deposit_scenario\filter_tools.py test
python deposit_scenario\filter_tools.py create
python deposit_scenario\filter_tools.py approve
python deposit_scenario\filter_tools.py retire-legacy
python deposit_scenario\filter_tools.py status
```

These commands wrap real `teststreamfilter`, `createrawsendfrom ... sign`, `create streamfilter`, `approvefrom`, `liststreamfilters` and `liststreams` calls. JSON-RPC avoids fragile Windows command-line JSON escaping. Credentials are read privately from the native node configurations, and exact chain names/ports are checked. The helper refuses `chain1`.

Compilation checks syntax. The six native tests execute signed candidate transactions without broadcasting. Creation requires passing tests for the exact source hash. Approval applies only to `bank_events`.

For an earlier installation, the new filter is approved **before** the known old `bank_deposit_rules` is disapproved. The archive `bank_filter_legacy.js` is retained to verify that exact old code before retirement. This avoids an unfiltered interval; while both incompatible filters remain active, new 40% publications are blocked. Unknown filters are never automatically removed. On a fresh installation the retirement command is a no-op. Repeated successful lifecycle steps do not duplicate creation/approval transactions.

Verify actual activation, not just `compiled: true`:

```cmd
multichain-cli.exe GreenAddress liststreams bank_events true
multichain-cli.exe GreenAddress liststreamfilters bank_deposit_rules_40 true
multichain-cli.exe GreenAddress getfiltercode bank_deposit_rules_40
multichain-cli.exe k269012 liststreamfilters
```

Expected: only `bank_deposit_rules_40` in the BANK stream's `filters`; no USER filter. The old filter may remain listed as created but inactive. In the Web Demo use **Filters: Stream**, not Transaction. On its approval page, do not approve the filter for `root`.

## 2. Demonstrate valid and invalid records

Open [GreenAddress Stream Filters](http://127.0.0.1:8000/?chain=greenaddress&page=streamfilter). Paste the complete current `bank_filter.js` into **Filter code**; the default sample is not the bank rule. Choose the local BANK publisher, `bank_events`, and **JSON (enter JSON below)**. Leave off-chain unchecked.

The unlabelled large textarea directly below the data-format dropdown is the JSON box. Set **Test publish item keys** to the JSON's exact `offer_id`, optionally followed by its event on a separate line. Use plain text, not quotes or a JSON array.

| JSON fixture | Required offer key | Expected result |
| --- | --- | --- |
| `examples/valid.json` | TEST40_VALID | Allowed |
| `examples/invalid_bonus.json` | TEST40_BAD_BONUS | Incorrect bonus amount |
| `examples/invalid_final.json` | TEST40_BAD_FINAL | Incorrect final amount |
| `examples/missing_field.json` | TEST40_MISSING | Missing required field: principal |

Click **Test Publishing Item with This Filter**, immediately below the JSON box. Test one case at a time, keeping the code unchanged. If the offer ID changes, update its key too. The filter returns the first failed rule; a key mismatch can mask the intended arithmetic error. Starting from valid JSON, changing the percentage to 50 or 60 must return `bonus_percent must be 40`.

These UI tests do not broadcast records and test the code in the textbox, not automatically the deployed code. For actual active-filter enforcement:

```cmd
python deposit_scenario\filter_tools.py publish-tests
```

This publishes one isolated valid `TEST40_VALID` fixture and attempts five invalid cases. Invalid attempts must be rejected by the real API with zero records for their keys. The valid fixture is not evidence of an accepted deposit workflow. Reports are saved separately under ignored `deposit_scenario/results/bank_deposit_rules_40/`. A dry-run result must not be described as a broadcast transaction.

## 3. Create an offer and obtain initial USER acceptance

The verified historical example is **DEP040**. For another run, choose an unused offer ID; commands below use **DEP041** as an example. If it already exists, choose another ID and use it consistently. Do not delete history or recreate chains.

Run one command at a time. Do not paste the entire walkthrough into a terminal containing interactive prompts.

```cmd
python deposit_scenario\demo.py offer DEP041 --principal 1000
python deposit_scenario\demo.py relay DEP041 --event DEPOSIT_OFFERED
```

After each command, wait for the confirmed receipt. Then ask the USER to accept:

```cmd
python deposit_scenario\demo.py accept-deposit DEP041 --amount 1000
```

Review principal 1,000, bonus 400, final 1,400, then type **ACCEPT** at the prompt. The `--amount` option supplies the deposit amount directly. If omitted, enter `1000` at the amount prompt before typing ACCEPT at the separate acceptance prompt. Blank/non-integer or mismatched amounts write no acceptance, and later steps correctly stop with a missing-event error. Any response other than ACCEPT cancels consent.

```cmd
python deposit_scenario\demo.py relay DEP041 --event DEPOSIT_ACCEPTED
```

This copies the USER acceptance to the BANK stream for filter validation. The helper verifies the actual source notice and adds its transaction/output/hash reference. It does not make the two chains read each other directly.

## 4. Simulate maturity and obtain bonus acceptance

```cmd
python deposit_scenario\demo.py mature DEP041
```

The timer displays **Month 1** through **Month 6**, then **Maturity reached**. One second represents one month only in this application simulation. The BANK records `MATURITY_REACHED / BONUS_READY`, not final credit. Wait afterward for transaction confirmation.

```cmd
python deposit_scenario\demo.py relay DEP041 --event MATURITY_REACHED
python deposit_scenario\demo.py accept-bonus DEP041
```

The first command sends the notification to the USER stream. Run the second only after that succeeds, review the available 400 bonus, and explicitly type **ACCEPT**. No second deposit is requested.

## 5. Complete and verify

```cmd
python deposit_scenario\demo.py relay DEP041 --event BONUS_ACCEPTED
python deposit_scenario\demo.py complete DEP041
python deposit_scenario\demo.py verify DEP041
```

Run separately, waiting for each confirmation. Completion requires both banked acceptances, valid source references, accepted original terms and the maturity record. Expected final account record: principal 1,000, bonus 400, final 1,400, status COMPLETED. Verification should report `verified: true`, five BANK events, four logical USER events and no duplicates for a clean run.

Inspect safely using:

```cmd
python deposit_scenario\demo.py status DEP041
multichain-cli.exe GreenAddress liststreamkeyitems bank_events DEP041
multichain-cli.exe k269012 liststreamkeyitems user_events DEP041
```

In the Web Demo select the correct chain, **View Streams**, its event stream, then the offer-ID key. Default native listing commands return up to ten items; use explicit count/start for larger histories. The helper checks up to 10,000 and refuses truncated results.

Already-recorded maturity and identical completion steps are no-ops. Conflicting duplicates stop processing. Identical repeated USER acceptances are retained on-chain but processed once and reported as replays; they are not silently deleted. This is sequential single-operator protection, not an atomic guarantee against concurrent/direct writers.

## Optional: USER acceptance through the Web Demo

Use **either** the CLI acceptance **or** the GUI for each event, never both. On the USER **Publish** page select `user_events`, leave off-chain unchecked, and generate the exact payload using:

```cmd
python deposit_scenario\demo.py acceptance-json DEP041
```

For initial acceptance, keys are `DEP041` and `DEPOSIT_ACCEPTED`, one per line. Paste the generated JSON under **Or JSON**, leave text/upload empty, review terms and click **Publish Item** once. For bonus acceptance after notification, generate using `acceptance-json DEP041 --bonus` and use the `BONUS_ACCEPTED` event key instead. Relay the resulting acceptance with the corresponding command above.

The helper refuses to prepare an acceptance that already exists. Prefilled fields belong to one browser tab only. A blank form is not an acceptance; do not submit it. Do not refresh a successful POST page. The Web Demo's **Accept Offer** menu is for asset exchange, not this scenario.

## Outputs and recovery

Generated files remain ignored under `deposit_scenario/results/`: filter reports in `bank_deposit_rules_40/`, `<offer>_timer.json`, `<offer>_verification.json`, and appended publication receipts in `workflow.jsonl`. A new clone does not include the original machine's private configuration or these generated reports. See [observed verification results](../docs/VERIFICATION.md).

If interrupted after a transaction ID is printed, Ctrl+C does not undo that transaction. Inspect status/confirmations and resume from the first missing step. Do not press Ctrl+C simply because confirmation is taking time, or rerun every command after an earlier failure. An interrupted publication can exist on-chain before its local receipt is written; the chains and verifier, not a complete-looking log file alone, establish the event history.
