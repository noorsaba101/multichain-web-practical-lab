"""Small localhost-only JSON-RPC client. Credentials are never printed or put in URLs."""
import base64
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

BANK = "GreenAddress"
USER = "k269012"
PORTS = {BANK: 6468, USER: 6478}
STREAMS = {BANK: "bank_events", USER: "user_events"}
FILTER = "bank_deposit_rules_40"
LEGACY_FILTER = "bank_deposit_rules"
BONUS_PERCENT = 40


class RPCError(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        super().__init__("RPC {}: {}".format(code, message))


def settings(path):
    values = {}
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator:
            values[key.strip()] = value.strip()
    return values


def credentials(chain):
    if chain not in PORTS:
        raise ValueError("This helper only permits GreenAddress and k269012; never chain1.")
    directory = Path(os.environ["APPDATA"]) / "MultiChain" / chain
    config = settings(directory / "multichain.conf")
    params = settings(directory / "params.dat")
    port = int(config.get("rpcport", params["default-rpc-port"].split("#", 1)[0]))
    if port != PORTS[chain]:
        raise ValueError("Unexpected RPC port for {}; inspect configuration privately.".format(chain))
    if not config.get("rpcuser") or not config.get("rpcpassword"):
        raise ValueError("Missing RPC credentials for {}; do not print the config.".format(chain))
    return port, config["rpcuser"], config["rpcpassword"]


class RPC:
    def __init__(self, chain):
        self.chain = chain
        port, username, password = credentials(chain)
        self.url = "http://127.0.0.1:{}/".format(port)
        self.authorization = "Basic " + base64.b64encode(
            (username + ":" + password).encode("utf-8")).decode("ascii")
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        if self.call("getinfo")["chainname"] != chain:
            raise ValueError("RPC identity mismatch; refusing this endpoint.")

    def call(self, method, *params):
        body = json.dumps({"jsonrpc": "1.0", "id": "exam", "method": method,
                           "params": list(params)}, allow_nan=False).encode("utf-8")
        request = urllib.request.Request(self.url, data=body, headers={
            "Content-Type": "application/json", "Authorization": self.authorization})
        try:
            with self.opener.open(request, timeout=15) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            try:
                result = json.loads(error.read().decode("utf-8"))
            except (ValueError, UnicodeError):
                raise RPCError(error.code, "HTTP failure; check node/authentication privately.") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise RPCError("connection", "Cannot reach {} on localhost. Is its node running?".format(self.chain)) from None
        if result.get("error"):
            raise RPCError(result["error"]["code"], result["error"]["message"])
        return result["result"]
