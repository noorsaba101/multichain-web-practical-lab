# MultiChain Web Practical Lab

A native Windows blockchain practical built on the official [MultiChain Web Demo](https://github.com/MultiChain/multichain-web-demo). This fork retains the PHP interface, adds PHP 8 compatibility fixes, and implements an independently relayed bank/student deposit demonstration using a **real MultiChain Stream Filter**.

## Practical scope

| Exercise | Implementation |
| --- | --- |
| Connect the Web Demo to a node | Localhost JSON-RPC; inspect chain identity, addresses and status |
| Issue and transfer an asset | Web Demo issuance and transfer of Goffycoin on `chain1` |
| Bank/student scenario | Two independent chains, separate event streams, explicit acceptances and an off-chain relay |
| Bank-side business rules | `filterstreamitem()` validates bank stream items through `getfilterstreamitem()` |
| Maturity and bonus | Six-second application timer representing six months; **40% only** |
| Verification | Source-transaction references, arithmetic, event ordering and duplicate checks |

This is an educational demonstration, not a banking service. The deposit balance is an **account/event record**, not evidence of a fiat deposit or an asset transfer.

## Architecture

| Chain | Role | Stream | RPC port | P2P port |
| --- | --- | --- | --- | --- |
| `chain1` | Original asset practical | Not used by the deposit helper | 6458 in the tested setup | 6459 in the tested setup |
| `GreenAddress` | BANK | `bank_events` | 6468 | 6469 |
| `k269012` | USER / student | `user_events` | 6478 | 6479 |

`GreenAddress` and `k269012` are independent blockchains, not two nodes of one chain. Python explicitly copies selected event data between them and records source transaction/output/hash references. Neither chain directly reads the other's stream, and no asset automatically crosses between them.

Only `GreenAddress/bank_events` has the active filter **`bank_deposit_rules_40`**. The USER chain has no Smart Filter.

## Deposit rule and flow

```text
BANK offer -> relay to USER -> USER accepts deposit -> relay to BANK
    -> Month 1 ... Month 6 -> BANK records maturity -> relay notification to USER
    -> USER accepts bonus -> relay to BANK -> BANK records COMPLETED
```

For principal **1,000**:

```text
bonus = 1000 * 40 / 100 = 400
final = 1000 + 400 = 1400
```

The maturity event makes the bonus available. Completion requires a second, explicit USER acceptance; it is not credited merely because the timer finishes. **One second represents one month only inside the helper's demonstration timer**, not inside MultiChain or the filter.

The former 50/60% filter is archived for upgrade/history purposes and must not remain active alongside the 40% filter. Historical offers are not rewritten to new terms.

## Run the practical

Tested with MultiChain Community **2.3.3**, PHP **8.4.25** with cURL/JSON, and Python **3.11** on native Windows. Python uses only its standard library. Node.js is optional for local JavaScript unit tests; the deployed filter runs in MultiChain's V8 engine.

1. Follow [Windows setup](docs/SETUP.md) to reuse or prepare the nodes, streams and private Web Demo configuration.
2. Run the [filter lifecycle and deposit walkthrough](deposit_scenario/README.md), one command at a time.
3. Review the [verification record and test results](docs/VERIFICATION.md).

Run commands from this repository's root. An existing PHP server may still serve a different clone; confirm its document root before reviewing changes. Do not start a second server on the same port.

### Asset practical

For a fresh exercise, perform these actions manually in the Web Demo:

1. On **Node**, verify the actual chain is `chain1` and node information loads successfully.
2. Identify sender A and receiver B; create a new address only if another is needed. Two wallet addresses do not mean two nodes.
3. On **Permissions**, verify A can issue/send/receive and B can receive. Grant only missing permissions through an authorized administrator.
4. On **Issue Asset**, issue **Goffycoin**, quantity **1,000**, units **1**, from A to A. Record the successful transaction ID and wait for confirmation.
5. On **Send**, send **100 Goffycoin** from A to B once. Do not refresh/resubmit the successful POST page.
6. Inspect the transaction and per-address asset balances. In this fresh example A has 900 and B has 100; report actual balances if the asset has other history. The corresponding RPC operations are `issuefrom`, `sendassetfrom` and `getaddressbalances`.

These are instructions for a **fresh exercise**, not permission to reissue an existing asset. If Goffycoin already exists, inspect its existing records/balances instead. The deposit scenario does not reuse `chain1` or Goffycoin. The UI's **Create Offer / Accept** pages are asset-exchange features, not the deposit acceptance mechanism.

## Validation

Local unit tests require no running chain and do not publish transactions:

```cmd
python -B -m unittest discover -s deposit_scenario\tests -v
node deposit_scenario\tests\test_filter.cjs
```

The verified revision passes **34 Python tests** and **21 JavaScript tests**. Native filter tests and real publish enforcement are separate steps documented in the walkthrough; only the latter broadcasts an isolated valid test fixture.

The completed local **DEP040** demonstration verified principal **1,000**, bonus **400**, final **1,400**, five BANK events, four USER events and no duplicate events or acceptance replays. Public transaction references and limitations are listed in [verification](docs/VERIFICATION.md). They identify a local development chain, not a public block explorer.

## Repository contents

- Root PHP/CSS files: inherited Web Demo and compatibility fixes.
- `deposit_scenario/`: relay, amount/acceptance logic, timer, filter lifecycle, examples and tests.
- `docs/SETUP.md`: native Windows setup and safe local operation.
- `docs/VERIFICATION.md`: observed results, test outcomes and public transaction references.
- `docs/UPSTREAM_README.md`: preserved original Web Demo README; reference only, not the Windows setup guide.
- `config-example.txt`: credential-free configuration template.
- `LICENSE.txt`: inherited GNU Affero General Public License, version 3.

`config.txt`, generated results, wallet/configuration secrets and personal preparation notes are excluded from the submission tree or ignored. Node data stays outside Git under `%APPDATA%\MultiChain`.

## Security and limitations

- Bind PHP to **127.0.0.1** and keep RPC local. This basic Web Demo has no production authentication layer; `config.txt` is plaintext and can be served by a basic web server. Do not expose this setup publicly.
- Never publish RPC passwords, wallet files or private keys. The fork intentionally does not include the original machine's private configuration or generated results.
- The filter validates the current item's fields and arithmetic. Relay reference fields describe a source but do not themselves prove external-chain truth; the helper checks them against the source node.
- Ordering, acceptance history and sequential duplicate handling belong to the helper. Direct publication can bypass that historical workflow; this is not a stateful banking contract or distributed exactly-once protocol.
- Stream-filter publish/retrieval checks should not be described as Ethereum execution or cross-chain consensus.
- A transaction ID means submission, not rollback protection. Wait for confirmation. If interrupted after submission, inspect status before retrying; do not recreate the offer or delete history.

## Attribution and license

**Upstream:** [MultiChain Web Demo](https://github.com/MultiChain/multichain-web-demo), Copyright (C) Coin Sciences Ltd. The original interface and its attribution are retained, and the original README is preserved in [docs/UPSTREAM_README.md](docs/UPSTREAM_README.md).

**Practical extensions:** Developed by [Noor us Saba (noorsaba101)](https://github.com/noorsaba101) for the MultiChain practical, student ID **k269012**. These contributions include:

- PHP 8.4 compatibility and balance-display fixes.
- The independent BANK/USER deposit workflow, explicit off-chain relay, user acceptances and six-month demonstration timer.
- The bank-only Stream Filter enforcing the 40% bonus rule and validating event fields and arithmetic.
- Automated tests, native Windows setup instructions and verification documentation.

This fork retains the upstream **GNU Affero General Public License, version 3**, in the unchanged root [LICENSE.txt](LICENSE.txt). Credit for the practical extensions does not replace the upstream authorship or license.
