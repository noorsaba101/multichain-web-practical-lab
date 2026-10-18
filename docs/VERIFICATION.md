# Verification results

## Observed local result: DEP040

The completed 40% demonstration was verified on 17 October 2026 using real native Windows MultiChain 2.3.3 nodes. This summary is transcribed from the generated `DEP040_verification.json` and native filter test reports in the original working environment; it is not a mock-chain result or a newly executed deposit.

| Check | Observed result |
| --- | --- |
| Offer/user | DEP040 / k269012 |
| Principal | 1,000 |
| Bonus | 40% = 400 |
| Final bank account record | 1,400; COMPLETED |
| Verification | `verified: true` |
| BANK events | Five ordered records |
| USER events | Four ordered records |
| Duplicate BANK events / USER acceptance replays | 0 / 0 |
| Filter | bank_deposit_rules_40, active only on bank_events |
| Filter source SHA256 | `9691aec40f0ea8a77ae86f071dbef6a0ab8b78f4ac94010974c4316ae505a70e` |

### BANK transaction references

| Event | Transaction ID |
| --- | --- |
| DEPOSIT_OFFERED | `5279e304c0892bf9cf704e50920ccfb41f9145e08b6e6dd077755784ec73c16b` |
| DEPOSIT_ACCEPTED | `4355502e4696dfb904696014a54f36a255597b6102b97ddaa14638170bb85e9e` |
| MATURITY_REACHED | `8a87a2bc4f3fe9eac8a9ae77ab52564a7873724cbc7444491113d1e1d1ac1075` |
| BONUS_ACCEPTED | `91864e60f95682001c598c89b71b5e17bd1d4872b39f6bf899706da60298deaf` |
| COMPLETED | `85c9a21bcec8ba85a9116948a09bd84adb1ac2f4125d90dab409166240111895` |

### USER transaction references

| Event | Transaction ID |
| --- | --- |
| DEPOSIT_OFFERED | `6526efff23bbe0c5e81e4b9188acea439189e489b5bde2681f65fb2e3e078e4b` |
| DEPOSIT_ACCEPTED | `5c68d6787cf78e0cf0b027ab30a9ce594c353a1a734ad985a05c46377b117483` |
| MATURITY_REACHED | `01f50c2f9fb1b65cbedf6e50d8363166ba8390798049628b9e57a8b489b359fe` |
| BONUS_ACCEPTED | `2bc61b14bf30b0a54039ccf3c873a192d8964f3468864912015219f9c402af1d` |

These identify transactions on the two local development chains, not a public Ethereum/MultiChain network. A new clone alone does not contain those chains or private/generated files. Reproduce the exercise on prepared nodes or inspect the original local nodes; do not fabricate matching transaction IDs for a fresh run.

## Filter validation results

Native V8 dry-run tests and real publish API tests covered the same six cases:

| Input | Native test / real publish outcome |
| --- | --- |
| 40%; principal 1,000, bonus 400, final 1,400 | Allowed / accepted |
| 40%; bonus 300, final 1,300 | Incorrect bonus amount / rejected |
| 40%; bonus 400, final 1,300 | Incorrect final amount / rejected |
| Missing principal | Missing required field: principal / rejected |
| 50% with matching 50% arithmetic | bonus_percent must be 40 / rejected |
| 60% with matching 60% arithmetic | bonus_percent must be 40 / rejected |

The actual invalid publish attempts returned RPC `-701` and left zero items under their test keys. The separate valid TEST40 fixture was published as `65ae12cb011690a61188b4a4a20d06593fee44d28210f10cb933865d46fb6cf4`. A structurally valid COMPLETED test fixture does not establish a legitimate deposit workflow; historical acceptance is enforced by the helper, not by the filter alone.

Local automated coverage: 34 Python tests and 21 JavaScript VM tests. Unit tests do not require live nodes and should not be presented as proof that transactions were broadcast. Generated native reports remain under ignored `deposit_scenario/results/bank_deposit_rules_40/` in the environment where they were run.

For another demonstration, use a new offer ID throughout. Do not recreate the chains, reissue an existing Goffycoin asset or delete history to make a repeated exercise appear fresh.
