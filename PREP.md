# MultiChain Windows practical preparation

Prepared 2026-10-17. Scope: official Web Demo connection and Goffycoin issuance/transfer. Tasks 3/4 are not started. No research files, existing chain configuration, or wallet files were manually edited (the running node maintains its own data normally). Never recreate `chain1`, delete its data, or disable security software to fix connectivity.

## Verified environment and current progress

- Native Windows MultiChain Community 2.3.3; chain `chain1`, protocol 20013.
- Existing chain was stopped; it has been started successfully. CLI and Web Demo both read its live status. Zero peers is expected for this local single-node exercise; it does not mean RPC failed.
- PHP 8.4.25 already installed; cURL and JSON are loaded. No software was installed. PHP's built-in development server is sufficient; Apache/XAMPP is not required.
- Demo `config.txt` parses correctly: prefix `default`, display name `Default`, `rpchost=127.0.0.1`, `rpcsecure=0`, `rpcport=6458`. Username/password match the node config; they are intentionally omitted here.
- RPC listeners: `127.0.0.1:6458` and `[::1]:6458`. Web listener: `127.0.0.1:8000`. P2P listens on port 6459.
- Minimal local demo fixes: `index.php`, `functions.php`, `page-default.php`, `page-issue.php`, `page-send.php`. Nullable string/count handling is PHP 8 compatible; Node's read-only balance query uses explicit `*` addresses/assets instead of empty lists, which returned no balances on this installation. Five files pass `php -l`; homepage, Node, Permissions, Issue Asset, and Send GET requests pass without PHP diagnostics. `config.txt` was not changed.
- Tasks 1 and 2: VERIFIED. You manually created B, granted Receive, issued 1000 Goffycoin to A, then sent 100 to B through the Web Demo. CLI independently verified the chain transactions, block confirmations, per-address changes and confirmed balances. Node displays both balances without PHP errors.
- Initial inspection had one wallet address and no Goffycoin. NOW Goffycoin exists: do not repeat the fresh-asset issuance example below. Use existing balances or ask the examiner how to handle a repeated demonstration; never reset the chain to hide prior activity.

### Actual rehearsal evidence (manual UI submissions)

| Operation | Transaction/reference | Verification |
| --- | --- | --- |
| Sender A | `19LYcoXd18gtm4VZrZHhRxJp6DXe9UaAREivd1` | Existing owned address; issue/send/receive/admin confirmed |
| Receiver B | `1L9vBbbz763E15iU5BLoMw78oYhWBe5jT4YRjq` | New owned address, manually created |
| Grant B Receive | `5dd168ff0139fab61eb9e40a79660783b76ad4c8563e840827c4f18f22cb8338` | CLI verified Receive-only grant; 11 confirmations at check |
| Issue Goffycoin | `fcf805bf607818dfa121f65b7230a1b2cacf5a4e617a1f1f796e5992f91dbda7` | Confirmed by CLI (2 confirmations at check); open=true, supply1000, units1, assetref `71-265-63740` |
| Send 100 A -> B | `cc66e623233c382f8873998c871a1edad862c58d59e09169f67eec75bf516b42` | Confirmed by CLI (3 confirmations at check); A change -100, B change +100 |
| Confirmed balances | A=900, B=100, total=1000 Goffycoin | Both `getaddressbalances ... 1` and `getmultibalances * * 1 true` agree; Node HTML independently displays two Goffycoin rows, 900 and100 |

## Important paths

| Item | Windows path |
| --- | --- |
| Practical root | `C:\D\PhD\1\Blockchain\multichain-practical` |
| Executables | `C:\D\PhD\1\Blockchain\multichain-practical\multichain` |
| Official demo clone | `C:\D\PhD\1\Blockchain\multichain-practical\multichain-web-demo` |
| Chain data | `C:\Users\Noor\AppData\Roaming\MultiChain\chain1` |
| Node credentials/runtime settings | `C:\Users\Noor\AppData\Roaming\MultiChain\chain1\multichain.conf` |
| Established chain parameters | `C:\Users\Noor\AppData\Roaming\MultiChain\chain1\params.dat` |
| Demo RPC settings (SECRET) | `C:\D\PhD\1\Blockchain\multichain-practical\multichain-web-demo\config.txt` |
| Existing PHP binary | `C:\D\Office\homewhitehelmet\tools\php84\php.exe` |
| Existing PHP ini | `C:\D\Office\homewhitehelmet\tools\php84\php.ini` |

Use Windows `%APPDATA%\MultiChain`, not WSL/Git Bash `~/.multichain`. Protect the wallet/private keys and both credential files. Do not commit `config.txt`, put credentials in commands/screenshots, or request it through the browser. The official demo can serve this text file; keep the development site strictly localhost-only.

Security finding: `config.txt` was staged in the demo Git repository at the final check. Do not commit/push that staged secret file. Its staging was not changed as part of setup.

## Startup: individual PowerShell commands

First check whether the node is already running (do not start a duplicate):

```powershell
Set-Location 'C:\D\PhD\1\Blockchain\multichain-practical'
.\multichain\multichain-cli.exe chain1 getinfo
```

If it cannot connect and no node process is starting, open terminal A and run:

```powershell
.\multichain\multichaind.exe chain1
```

Keep terminal A open. This starts the EXISTING chain. The bundled Windows README explicitly says `-daemon` does not work as on Linux; do not rely on it. Do NOT run `multichain-util create chain1`.

In terminal B, start the website (leave this terminal open too):

```powershell
Set-Location 'C:\D\PhD\1\Blockchain\multichain-practical\multichain-web-demo'
php -S 127.0.0.1:8000
```

`-S` starts PHP's development HTTP server; the current folder is the document root and contains `config.txt`. If `php` is not on PATH, use the existing binary instead:

```powershell
& 'C:\D\Office\homewhitehelmet\tools\php84\php.exe' -S 127.0.0.1:8000
```

Open `http://127.0.0.1:8000/?chain=default` in a browser. `default` is the demo CONFIG PREFIX, not a different blockchain. The page header can say Default; My Node > Name must say `chain1`. Use a wide browser window; the old demo hides its navigation at narrow widths. Direct pages: `/?chain=default&page=permissions`, `/?chain=default&page=issue`, `/?chain=default&page=send` on the same localhost site.

## Commands to memorize (terminal C, practical root)

| PowerShell command | Purpose |
| --- | --- |
| `.\multichain\multichain-cli.exe chain1 getinfo` | RPC connection, chain name/version, blocks, errors, advertised node address, P2P port and peer count |
| `.\multichain\multichain-cli.exe chain1 getpeerinfo` | Actual P2P peers; empty array is normal with one node |
| `.\multichain\multichain-cli.exe chain1 getaddresses true` | Wallet addresses and `ismine` (private key held locally), NOT private key export |
| `.\multichain\multichain-cli.exe chain1 getnewaddress` | Generate another address/key in this wallet; does not grant permissions |
| `.\multichain\multichain-cli.exe chain1 listpermissions` | Explicit permission grants |
| `.\multichain\multichain-cli.exe chain1 listassets Goffycoin true` | Asset definition, issuance details and txid; not found is expected before creation |
| `.\multichain\multichain-cli.exe chain1 help sendassetfrom` | Installed version's exact command arguments |
| `.\multichain\multichain-cli.exe chain1 stop` | Graceful node shutdown; preserves the chain/wallet |
| `php -v`, `php --ini`, `php -m` | PHP version, active configuration, cURL/JSON modules |
| `ipconfig` | Identify active Wi-Fi/Ethernet IPv4 for a later LAN peer |

Stop PHP with Ctrl+C in its server terminal. PHP and MultiChain are independent: stopping either does not stop the other. Preparation started them as hidden background processes, so no terminal may be visible for those instances. To stop that PHP instance, first run `Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object OwningProcess`, inspect the returned PID with `Get-Process -Id <PID>`, and only if it is the expected PHP server use `Stop-Process -Id <PID>` (replace placeholders). Stop the node only with the CLI `stop`. Do not stop unrelated PHP processes.

## Task 1: explain and demonstrate the connection

Browser on port 8000 -> PHP Web Demo -> authenticated HTTP JSON-RPC on 127.0.0.1:6458 -> `multichaind` -> chain1. The browser does not communicate over the blockchain P2P port.

| Port | Role | Current setting |
| --- | --- | --- |
| 8000 | Browser -> PHP HTTP web server | Localhost only |
| 6458 | PHP/CLI -> node JSON-RPC API | `default-rpc-port`; loopback only |
| 6459 | Node -> node P2P blockchain traffic | `default-network-port` |

On Node, show My Node > Name `chain1`, Version `2.3.3`, Blocks, Node address, Peers, and My Addresses. Compare `getinfo` and `getaddresses true`; refresh to read updated blocks. Successful live values without an RPC error prove the website can authenticate and query this node. Peers/Connected Nodes refer to blockchain peers, NOT the PHP connection. `getinfo.errors` should be empty; `miningpaused` and `incomingpaused` should be false.

## Task 2: manual Goffycoin rehearsal

Use two addresses in THIS wallet; that demonstrates an address-to-address transfer, not a second independent computer/node. Do not issue again if the asset already exists. The example quantities below are for a fresh asset; otherwise check actual starting balances and examiner instructions.

1. Node > My Addresses: use existing address **A** `19LYcoXd18gtm4VZrZHhRxJp6DXe9UaAREivd1`. Its existing permissions include issue/send/receive/admin. Copy addresses accurately; never select the burn address.
2. Click **Get new address** ONCE. Copy the new address **B**; it will initially have no explicit permissions. A new address is a key pair in the same wallet, not a new blockchain.
3. Click **Permissions** (or B's **change** link). Admin address: A. For address: B. Operation: **Grant**. Select **Receive** only for this receiving-only task. Click **Change Permissions**. Wait for confirmation and check B now has receive. Grant Send too only if B must later send; do not grant Admin/Mine/Issue broadly.
4. Click **Issue Asset**. From address: A. Asset name: **Goffycoin** (exact spelling/case). Quantity: **1000**. Units: **1** (whole coins; this is the smallest transferable amount, not the supply). To address: A. Leave upload/custom fields blank. Click **Issue Asset** once. Record the returned issuance txid; wait for a block. The official demo creates an OPEN asset (further issuance allowed), even if that was not a separate input.
5. Verify Goffycoin in **Issued Assets**, quantity 1000 and units 1; Node should show A's Goffycoin balance 1000.
6. Click **Send**. From address: A. Asset name: Goffycoin. To address: **B, not A**. Quantity: **100**. Click **Send Asset** once; record the transfer txid and wait for confirmation. Do not refresh/resubmit a POST if the outcome is uncertain: check balances/transactions first.
7. Return to **Node** or **Send > Available Balances**. Expected for exactly this fresh example: A = **900**, B = **100** Goffycoin, total = 1000. Node shows B even if B has no Send permission; Send's Available Balances only lists send-capable addresses.
8. Use the read-only CLI below to inspect txid/confirmations and per-address changes. The official Web Demo has no full transaction-history viewer, so a CLI transaction inspection complements the UI evidence.

### CLI equivalents: understand, do NOT repeat after UI submission

Replace `ADDRESS_A`, `ADDRESS_B`, and `TRANSFER_TXID` with actual values. These are separate commands; issuance/send/grant are real chain writes. No RPC password is necessary because the CLI reads the node config.

```powershell
.\multichain\multichain-cli.exe chain1 getnewaddress
.\multichain\multichain-cli.exe chain1 grant ADDRESS_B receive
```

The UI uses `grantfrom A B receive`; `grant` lets the wallet choose an eligible administrator. Sending with no metadata uses exactly:

```powershell
.\multichain\multichain-cli.exe chain1 sendassetfrom ADDRESS_A ADDRESS_B Goffycoin 100
```

The UI issues via `createrawsendfrom` with asset-creation metadata (including `open=true`). Equivalent high-level OPEN issuance in **CMD**, using compact JSON with no spaces or extra outer quotes:

```cmd
multichain\multichain-cli.exe chain1 issuefrom ADDRESS_A ADDRESS_A {"name":"Goffycoin","open":true} 1000 1
```

In the preparation's native CMD invocation, a read-only `getmultibalances ["ADDRESS_A"] [] 0 true` query accepted this compact JSON style. An extra outer quote/backslash-escaped form retained unwanted literal quotes and failed; do not copy Linux quoting blindly. For these exam tasks the UI avoids JSON quoting entirely. A simpler PowerShell or CMD `issuefrom ADDRESS_A ADDRESS_A Goffycoin 1000 1` creates a CLOSED asset by default, so it is not identical to the demo. Do not run either issuance after already issuing through the interface.

Read-only verification (0 includes unconfirmed balances, 1 requires a confirmed block):

```powershell
.\multichain\multichain-cli.exe chain1 listassets Goffycoin true
.\multichain\multichain-cli.exe chain1 getaddressbalances ADDRESS_A 0
.\multichain\multichain-cli.exe chain1 getaddressbalances ADDRESS_B 0
.\multichain\multichain-cli.exe chain1 getaddressbalances ADDRESS_A 1
.\multichain\multichain-cli.exe chain1 getaddressbalances ADDRESS_B 1
.\multichain\multichain-cli.exe chain1 getrawtransaction TRANSFER_TXID 1
.\multichain\multichain-cli.exe chain1 getaddresstransaction ADDRESS_A TRANSFER_TXID true
.\multichain\multichain-cli.exe chain1 getaddresstransaction ADDRESS_B TRANSFER_TXID true
```

Check confirmations >=1, outputs to B, Goffycoin quantities, A's -100 and B's +100 change. `getwallettransaction` can show zero NET asset movement because A and B are in the SAME wallet; per-address commands avoid that ambiguity. If B has no previous outputs, an empty balance list before receiving means zero assets.

## Common errors and fixes

| Symptom | Check/fix |
| --- | --- |
| CLI cannot connect / EOF | Is the existing node running? Correct chain/config and RPC 6458? Allow startup time; do not recreate chain. |
| Data directory locked / port in use | A node/server may already run in the background. Identify process/port first; do not delete lock/wallet files or launch duplicates. |
| Browser refused connection | Start PHP on 8000; use `http://`, not `https://`; keep the PHP terminal open. |
| HTTP 401 / RPC unauthorized | Privately compare rpcuser/rpcpassword with the target node config; do not print them. Check demo key spelling, prefix, port. |
| HTTP 403 / remote RPC denied | Remote PHP server needs a SPECIFIC rpcallowip and scoped firewall rule; not needed for localhost. Do not use broad wildcards. |
| PHP cURL missing | `php --ini` / `php -m`; ensure you are using the already-tested PHP binary/ini. Do not install another stack first. |
| PHP count(null) / null-string deprecation | Keep the five documented compatibility fixes; do not suppress fatal errors or change global PHP settings. |
| Config seems missing | Start PHP from the demo folder; `functions.php` reads relative `config.txt`. |
| Navigation missing | Widen the browser; this old demo collapses navigation at small widths. Direct page URLs above work too. |
| B absent from To dropdown / permission denied | Grant Receive to B, wait for confirmation, reload; A needs Issue for creation and Send for sending. |
| Empty From/Asset on Send | No spendable assets yet, no Send permission, wrong address, locked outputs or a pending issuance; inspect actual balances first. |
| Asset already exists | Do NOT issue again. Inspect it and existing balances; ask examiner before choosing a different asset name. |
| Insufficient funds / invalid quantity | Check A's spendable Goffycoin, select the correct asset, and use multiples of Units (1 here). |
| Pending transactions never confirm | Check getinfo, getpeerinfo, listpermissions mine and miningpaused. Idle blocks can stop normally due to empty-block limits; test confirmations after a real transaction. Do not blindly grant Mine or change consensus parameters. |

## Later remote-node preparation (DOCUMENTATION ONLY; not configured)

1. On first PC: `ipconfig` -> active Wi-Fi/Ethernet IPv4 (same reachable LAN as second PC). Wi-Fi was `192.168.18.6` during preparation; recheck on exam day. Ignore disconnected/VPN/WSL/virtual adapters. `getinfo` advertised `chain1@172.31.16.1:6459`, but that IP belongs to the WSL virtual adapter. A same-Wi-Fi peer would normally try `chain1@192.168.18.6:6459` after checking reachability/firewall; do not blindly use the advertised virtual IP.
2. Second PC needs native MultiChain, its OWN wallet/data and a free local port. Do not copy the first PC's wallet or run create/clone for an independent chain of the same name. In its executable folder, the documentation's general connection form is `multichaind chain1@<FIRST-PC-IP>:<NETWORK-PORT> -daemon`. On this Windows build use `multichaind.exe chain1@<FIRST-PC-IP>:6459` in a separate terminal (omit the ineffective -daemon flag).
3. On a permissioned chain the first attempt reports the second node's wallet/handshake address and asks for connect permission. Copy that address to the administrator on the first PC. First PC: `multichain-cli.exe chain1 grant <SECOND_NODE_ADDRESS> connect`. This is an on-chain permission grant, not an IP firewall rule. Do not grant Admin/Mine just to connect. Wait for the grant to confirm.
4. If the initial attempt exited, second PC reconnects using `multichaind.exe chain1` (Windows), or the full address form if discovery needs it. Generic daemon-capable builds use `multichaind chain1 -daemon`. Do not launch a second process if the first is still waiting/retrying.
5. On each PC: `multichain-cli.exe chain1 getpeerinfo` and `getinfo`. Confirm a real peer/handshake and synchronized block heights, not merely an open socket. A transport-only test on PC2 is `Test-NetConnection <FIRST-PC-IP> -Port 6459` (PowerShell).
6. P2P uses TCP **6459**, NOT RPC6458 or HTTP8000. Only if required, create a Windows Firewall inbound allow rule for the specific MultiChain executable/TCP6459 on the appropriate Private profile, scoped to the second PC's IP (or exam LAN if explicitly approved). Never disable Defender/firewall, allow all ports, or expose RPC through router forwarding. If the network is Public, have the administrator approve appropriate exam-network rules; do not broaden profiles casually.
7. Remote PHP -> first PC RPC is a DIFFERENT setup, not needed for P2P joining. After approval, gracefully stop the node, add `rpcallowip=<WEB_SERVER_PC_IP>` to that node's `multichain.conf`, and restart. Allow TCP6458 inbound only from that specific PHP server IP; verify actual listener bindings/reachability and installed `multichaind.exe -help` before considering any bind override. Keep existing localhost access. Do not change established `params.dat` ports.
8. On the remote Web Demo set rpchost to the NODE'S reachable IP and rpcport=6458; use that node's RPC credentials privately. rpcallowip refers to the PHP SERVER'S IP, not necessarily the browser's IP. The peer's own local demo can instead target its own localhost RPC, avoiding remote credential transport entirely. Keep browser access to the demo local and protect its plaintext config.txt. Plain HTTP RPC has no encryption: prefer a trusted isolated exam LAN or an approved encrypted tunnel; do not send credentials over public/untrusted networks. rpcsecure=1 only works with a genuinely configured TLS endpoint, not by toggling it alone.

## Screenshot / evidence checklist

- [ ] Task 1: browser URL and Node panel showing chain1, version, blocks and peers.
- [ ] CLI getinfo matching the website (no credential files or private keys visible).
- [ ] A and B addresses and required permissions (public addresses only).
- [ ] Issue Asset form before submission: Goffycoin, 1000, Units1, From A / To A.
- [ ] Issuance success and txid; Issued Assets definition.
- [ ] Send form before submission: A -> B, Goffycoin100.
- [ ] Transfer success and txid.
- [ ] Confirmed per-address balances A900 / B100 and transaction confirmations.
- [ ] Record actual A/B, issuance/transfer txids and confirmed balances AFTER the manual rehearsal; never fabricate these entries.

Exam explanation: "The PHP interface authenticates to my existing node over JSON-RPC. I create an on-chain asset, then sign an asset transfer with the sender's wallet key. Receive permission controls the recipient's eligibility. A transaction ID identifies the operation; block confirmations and separate address balances verify it. Two addresses here do not mean two nodes."

References: [Official Web Demo](https://github.com/MultiChain/multichain-web-demo), [API](https://www.multichain.com/developers/json-rpc-api/), [connecting nodes](https://www.multichain.com/developers/creating-connecting/), [runtime settings](https://www.multichain.com/developers/runtime-parameters/). For native Windows flags/quoting, also read `multichain\README.txt` and the installed command's `help` output.
