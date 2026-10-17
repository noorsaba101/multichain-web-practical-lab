Yes. For your **Windows/CMD setup**, think of them in these groups. When using Windows, normally write the full prefix:

```cmd
multichain-cli chain1 <command>
```

### Quick exam cheat sheet

| Purpose | What it does | Example |
|---|---|---|
| **Create a blockchain** | Creates the chain configuration/`params.dat` | `multichain-util create PaymentChain` |
| **Start blockchain node** | Starts that chain and creates genesis block if first run | `multichaind PaymentChain -daemon` |
| **Check chain/node** | Shows general blockchain/node information | `multichain-cli PaymentChain getinfo` |
| **Create stream** | Creates a blockchain data stream | `multichain-cli chain1 create stream myStream true` |
| **Subscribe to stream** | Makes your node index/track the stream | `multichain-cli chain1 subscribe myStream` |
| **Publish stream item** | Writes data into the stream | example below |
| **Read stream** | Displays stream records | `multichain-cli chain1 liststreamitems myStream` |
| **Issue asset** | Creates a new asset and gives initial quantity to an address | `multichain-cli chain1 issue <ADDRESS> Goffycoin 1000 1` |
| **Send asset** | Sends asset from wallet automatically | `multichain-cli chain1 sendasset <RECEIVER> Goffycoin 100` |
| **Send from specific address** | Explicitly chooses sender | `multichain-cli chain1 sendassetfrom <SENDER> <RECEIVER> Goffycoin 100` |
| **Grant permission** | Gives another address chain/stream permissions | `multichain-cli chain1 grant <ADDRESS> connect,send,receive` |
| **Create filter** | Stores Smart Filter JavaScript on chain | example below |
| **Test filter** | Checks filter code/behavior before activation | example below |
| **Approve filter** | Activates filter for a stream | example below |
| **Connect second PC** | Joins another node to same chain | `multichaind chain1@192.168.1.10:NETWORK_PORT -daemon` |

These command forms follow MultiChain's current CLI/API documentation. [MultiChain](https://www.multichain.com/developers/json-rpc-api/?utm_source=chatgpt.com)

---

## 1. Create a new chain

For example, if Sir asks:

> Create a blockchain named `PaymentChain`

```cmd
multichain-util create PaymentChain
```

Then start it:

```cmd
multichaind PaymentChain -daemon
```

Check it:

```cmd
multichain-cli PaymentChain getinfo
```

So remember:

```text
multichain-util create = make chain
multichaind -daemon     = run chain
multichain-cli getinfo  = inspect chain
```

MultiChain creates the chain directory under `%APPDATA%\MultiChain\` on Windows. [MultiChain](https://www.multichain.com/developers/creating-connecting/?utm_source=chatgpt.com)

---

## 2. Create a stream

Streams are for storing records/data on the blockchain.

Example:

```cmd
multichain-cli chain1 create stream payment_requests true
```

Here:

```text
stream            = entity type
payment_requests  = stream name
true              = open stream
```

`true` means participants with global `send` permission can publish to it. [MultiChain](https://www.multichain.com/developers/data-streams/?utm_source=chatgpt.com)

Check streams:

```cmd
multichain-cli chain1 liststreams
```

---

## 3. Subscribe to a stream

After creation:

```cmd
multichain-cli chain1 subscribe payment_requests
```

This tells your node to index/track the stream. [MultiChain](https://www.multichain.com/developers/json-rpc-api/?utm_source=chatgpt.com)

---

## 4. Publish a stream item

Suppose:

```text
stream = payment_requests
key    = REQ001
data   = {"amount":1000}
```

In **Windows CMD**:

```cmd
multichain-cli chain1 publish payment_requests REQ001 "{\"json\":{\"amount\":1000}}"
```

Then read the records:

```cmd
multichain-cli chain1 liststreamitems payment_requests
```

You can also retrieve by key later:

```cmd
multichain-cli chain1 liststreamkeyitems payment_requests REQ001
```

This is likely important for your `REQ001` duplicate check.

---

## 5. Issue an asset

First get/create an address:

```cmd
multichain-cli chain1 getnewaddress
```

Suppose it returns:

```text
1ABC123...
```

Create 1,000 Goffycoin:

```cmd
multichain-cli chain1 issue 1ABC123... Goffycoin 1000 1
```

Meaning:

```text
1ABC123... = address receiving initial issuance
Goffycoin  = asset name
1000       = quantity
1          = smallest unit
```

This is essentially what you already did successfully through Web Demo. [MultiChain](https://www.multichain.com/developers/json-rpc-api/?utm_source=chatgpt.com)

Check:

```cmd
multichain-cli chain1 listassets
```

---

## 6. `sendasset` vs `sendassetfrom`

### `sendasset`

You specify only the destination:

```cmd
multichain-cli chain1 sendasset <RECEIVER> Goffycoin 100
```

MultiChain chooses suitable funds from your node wallet.

### `sendassetfrom`

You explicitly specify both addresses:

```cmd
multichain-cli chain1 sendassetfrom <SENDER> <RECEIVER> Goffycoin 100
```

This is better when Sir specifically asks:

> Send from address A to address B. [MultiChain](https://www.multichain.com/developers/json-rpc-api/?utm_source=chatgpt.com)


---

## 7. Grant permissions

MultiChain is permissioned, so addresses can receive capabilities.

For another node:

```cmd
multichain-cli chain1 grant <ADDRESS> connect
```

For normal participation:

```cmd
multichain-cli chain1 grant <ADDRESS> connect,send,receive
```

If an address needs to create streams/assets:

```cmd
multichain-cli chain1 grant <ADDRESS> create,issue
```

For administrative ability:

```cmd
multichain-cli chain1 grant <ADDRESS> admin
```

Check permissions:

```cmd
multichain-cli chain1 listpermissions
```

For a particular stream you can also use per-stream permissions such as:

```cmd
multichain-cli chain1 grant <ADDRESS> payment_requests.write
```

MultiChain supports global permissions including `connect`, `send`, `receive`, `create`, `issue`, `mine`, `activate`, and `admin`. [MultiChain](https://www.multichain.com/developers/json-rpc-api/?utm_source=chatgpt.com)

---

# 8. Smart Filter: create → test → approve

This one is worth understanding conceptually:

```text
JavaScript filter code
        ↓
test it
        ↓
create filter on blockchain
        ↓
approve it for a stream
        ↓
new stream items are checked
```

Suppose Sir asks for a filter requiring **at least two keys**.

### Test before creating

In CMD:

```cmd
multichain-cli chain1 teststreamfilter "{}" "function filterstreamitem() { var item=getfilterstreamitem(); if (item.keys.length<2) return \"At least two keys required\"; }"
```

If it compiles correctly, create it:

```cmd
multichain-cli chain1 create streamfilter filter1 "{}" "function filterstreamitem() { var item=getfilterstreamitem(); if (item.keys.length<2) return \"At least two keys required\"; }"
```

Check:

```cmd
multichain-cli chain1 liststreamfilters
```

Get your admin address:

```cmd
multichain-cli chain1 listpermissions admin
```

Suppose it gives:

```text
1ADMINADDRESS...
```

Approve `filter1` for `myStream`:

```cmd
multichain-cli chain1 approvefrom 1ADMINADDRESS... filter1 "{\"for\":\"myStream\",\"approve\":true}"
```

Then check:

```cmd
multichain-cli chain1 liststreams myStream true
```

A stream filter must define:

```javascript
function filterstreamitem()
```

and returning a non-empty string means **reject the item**. [MultiChain](https://www.multichain.com/developers/smart-filters/?utm_source=chatgpt.com)

For the exam, the **Web Demo Smart Filters page may be easier** for writing/testing/approving them; the official Web Demo explicitly supports this. [MultiChain](https://www.multichain.com/developers/smart-filters/?utm_source=chatgpt.com)

---

# 9. Second node / another computer

Suppose your first computer shows its node address as:

```text
chain1@192.168.1.10:6459
```

On **PC 2**:

```cmd
multichaind chain1@192.168.1.10:6459 -daemon
```

Important:

```text
6458 = could be RPC port
6459 = could be NETWORK port
```

Use the **network port shown by your actual chain**, not my example number.

The second computer may initially say it does not have permission and display an address such as:

```text
1SECONDPC...
```

Back on **PC 1**:

```cmd
multichain-cli chain1 grant 1SECONDPC... connect
```

Then on PC 2:

```cmd
multichaind chain1 -daemon
```

Check peers:

```cmd
multichain-cli chain1 getpeerinfo
```

The `chain@IP:port` address uses the **peer/network port**, not the RPC port used by Web Demo. [MultiChain](https://www.multichain.com/getting-started/?utm_source=chatgpt.com)

---

### The ones I'd memorize first

```cmd
multichain-util create chain1
multichaind chain1 -daemon
multichain-cli chain1 getinfo

multichain-cli chain1 create stream stream1 true
multichain-cli chain1 subscribe stream1
multichain-cli chain1 publish stream1 key1 "{\"json\":{\"message\":\"hello\"}}"
multichain-cli chain1 liststreamitems stream1

multichain-cli chain1 issue <ADDRESS> Goffycoin 1000 1
multichain-cli chain1 sendasset <ADDRESS> Goffycoin 100

multichain-cli chain1 grant <ADDRESS> connect,send,receive

multichain-cli chain1 getpeerinfo
```

If you know **what these commands mean**, Codex can fill in the more complicated Smart Filter syntax during the practical without you being lost.