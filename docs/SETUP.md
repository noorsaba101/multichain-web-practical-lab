# Native Windows setup

Commands below use **CMD**, from the repository root, with the installed MultiChain executables available on PATH. If they are not on PATH, use their actual full paths; in the tested sibling-folder layout the prefix is `..\multichain\`. Do not install replacements merely because the binaries are not on PATH.

## 1. Inspect prerequisites and existing data

Use the existing native Windows MultiChain 2.3.3 installation, PHP with cURL/JSON, and Python. Apache, XAMPP and WSL are not required; PHP's built-in development server is sufficient for this localhost-only practical.

```cmd
php -v
php -m
python --version
multichain-cli.exe chain1 getinfo
multichain-cli.exe GreenAddress getinfo
multichain-cli.exe k269012 getinfo
```

An unreachable node may simply be stopped. Check `%APPDATA%\MultiChain\<chain>` before taking action. That is the native Windows data directory; WSL's `~/.multichain` is not the active data store for this setup. Never delete existing data or rerun chain creation as a connectivity fix.

## 2. Prepare only missing scenario chains

**Skip creation entirely for each chain whose data directory already exists.** The following are fresh-setup commands, not commands to rerun on the verified environment:

```cmd
multichain-util.exe create GreenAddress -default-network-port=6469 -default-rpc-port=6468
multichain-util.exe create k269012 -default-network-port=6479 -default-rpc-port=6478
```

Start each stopped node in its own CMD window and leave it running:

```cmd
multichaind.exe GreenAddress
```

```cmd
multichaind.exe k269012
```

The native Windows build does not provide Linux-style `-daemon` operation. Do not start duplicate instances. Use another terminal to run `getinfo` and verify the exact chain names before publishing. Existing `chain1` remains separate; start it only if needed for the asset practical, without recreating it.

The Python helper intentionally permits only GreenAddress RPC 6468 and k269012 RPC 6478. A different existing port causes a fail-closed error; inspect the setup rather than broadly changing RPC/firewall permissions. P2P ports connect peers; RPC ports serve CLI/PHP/helper requests. These independent chains are not joined as peers of one ledger.

## 3. Create and subscribe to missing streams

Inspect first:

```cmd
multichain-cli.exe GreenAddress liststreams bank_events true
multichain-cli.exe k269012 liststreams user_events true
```

If a stream does not exist, create that stream only:

```cmd
multichain-cli.exe GreenAddress create stream bank_events false
multichain-cli.exe k269012 create stream user_events false
```

Here `false` makes writing permission-controlled. The helper uses each stream's local creator address as publisher; it is an educational single-operator arrangement, not separate authenticated bank/student users. Wait for stream creation confirmation, then subscribe if not already subscribed:

```cmd
multichain-cli.exe GreenAddress subscribe bank_events
multichain-cli.exe k269012 subscribe user_events
```

Verify `liststreams` again. Both should be subscribed. Do not create a USER-chain Smart Filter.

## 4. Configure the Web Demo privately

The fork does not ship the original machine's `config.txt`. Create it from the template only if it is missing:

```cmd
if not exist config.txt copy config-example.txt config.txt
```

Privately edit the `default.*` entry for the existing `chain1` node. Set localhost, its actual RPC port, and the RPC username/password from `%APPDATA%\MultiChain\chain1\multichain.conf`. The tested chain1 RPC port was 6458; use the actual configuration, not the template's 12345 placeholder. Keep these values out of terminal output and Git.

With both scenario nodes running, append/check their entries using:

```cmd
python deposit_scenario\configure_web_demo.py
```

This reads the two native node configurations privately, verifies exact RPC chain identity, preserves the existing entry and adds `greenaddress.*` and `k269012.*`. It refuses mismatched existing entries rather than replacing them. It expects `config.txt` to exist first.

## 5. Start PHP and verify chain switching

From the repository root, in a separate terminal:

```cmd
php -S 127.0.0.1:8000
```

If another server already occupies port 8000, stop it with Ctrl+C in its own terminal before switching document roots, or use port 8001 and adjust the browser URL. Do not terminate unrelated processes or assume the old server automatically serves this clone.

Visit:

- [Original node](http://127.0.0.1:8000/?chain=default)
- [GreenAddress BANK](http://127.0.0.1:8000/?chain=greenaddress)
- [k269012 USER](http://127.0.0.1:8000/?chain=k269012)

Confirm actual chain identity, owned public addresses and successful node information for each. Zero peers is normal for a local single-node chain and does not mean RPC failed. Never publish until the heading and node identity match the intended chain.

Next follow the [filter and deposit walkthrough](../deposit_scenario/README.md). The Web Demo's **Filters: Stream** page is distinct from **Filters: Transaction** and the approval page; the bank filter belongs to the former.

## 6. Stop gracefully

Stop PHP using Ctrl+C in its terminal. Stop only the intended node using:

```cmd
multichain-cli.exe GreenAddress stop
multichain-cli.exe k269012 stop
```

Do not stop or reconfigure unrelated chains. Keep RPC and the PHP server restricted to localhost; no public RPC exposure or broad firewall exceptions are required.
