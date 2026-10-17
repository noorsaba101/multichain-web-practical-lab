"""Append only the two new localhost entries, without exposing passwords."""
from pathlib import Path
from rpc_client import BANK, USER, RPC, credentials


def main():
    path = Path(__file__).resolve().parent.parent / "config.txt"
    original = path.read_bytes()
    parsed = {}
    for line in original.decode("utf-8-sig").splitlines():
        entry = line.split("#", 1)[0].strip()
        if "=" in entry:
            key, value = entry.split("=", 1)
            parsed[key.strip()] = value.strip()
    additions = []
    for chain, prefix, label in [(BANK, "greenaddress", "GreenAddress BANK"),
                                  (USER, "k269012", "k269012 USER")]:
        RPC(chain)  # Verify endpoint identity before changing the demo.
        port, username, password = credentials(chain)
        expected = {"name": label, "rpchost": "127.0.0.1", "rpcsecure": "0",
                    "rpcport": str(port), "rpcuser": username, "rpcpassword": password}
        existing = {key.split(".", 1)[1]: value for key, value in parsed.items()
                    if key.startswith(prefix + ".")}
        if existing:
            if existing != expected:
                raise ValueError("Existing {} entry differs; refusing replacement.".format(prefix))
            print("{}: already configured (credentials hidden)".format(chain))
        else:
            additions.append("\r\n# Independent exam chain: {}\r\n".format(chain) +
                             "".join("{}.{}={}\r\n".format(prefix, key, value)
                                     for key, value in expected.items()))
    if additions:
        if path.read_bytes() != original:
            raise ValueError("Config changed during preparation; no write performed.")
        # Mechanical append preserves the pre-existing chain1 entry byte for byte.
        with path.open("ab") as handle:
            handle.write(("\r\n" + "".join(additions)).encode("utf-8"))
        assert path.read_bytes().startswith(original)
    print("Demo entries: default -> chain1; greenaddress -> GreenAddress; k269012 -> k269012")
    print("Original entry preserved. No credentials printed or chain data changed.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, RuntimeError) as error:
        raise SystemExit(str(error))
