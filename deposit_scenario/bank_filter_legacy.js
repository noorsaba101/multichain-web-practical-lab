// Real MultiChain stream filter. Deploy ONLY on GreenAddress; approve ONLY for bank_events.
// This validates the current item, not historical ordering, external-chain truth or elapsed time.
function filterstreamitem() {
    var item = getfilterstreamitem();
    if (!item || !item.data || !item.data.json ||
        typeof item.data.json !== "object" || Array.isArray(item.data.json))
        return "JSON object data required";
    var d = item.data.json;
    var required = ["schema_version", "offer_id", "user_id", "event", "status",
                    "principal", "bonus_percent", "maturity_months", "actor_role",
                    "source_chain", "destination_chain"];
    for (var i = 0; i < required.length; i++)
        if (!Object.prototype.hasOwnProperty.call(d, required[i]))
            return "Missing required field: " + required[i];
    if (d.schema_version !== 1) return "Unsupported schema version";
    if (typeof d.offer_id !== "string" || !/^[A-Za-z0-9_-]{1,40}$/.test(d.offer_id))
        return "Invalid offer_id";
    if (d.user_id !== "k269012") return "Invalid user_id";
    if (!item.keys || item.keys.indexOf(d.offer_id) < 0)
        return "Stream key must include offer_id";
    function integer(n) {
        return typeof n === "number" && isFinite(n) && Math.floor(n) === n;
    }
    if (!integer(d.principal) || d.principal <= 0 || d.principal > 1000000000)
        return "Principal must be a positive integer at most 1000000000";
    if (d.bonus_percent !== 50 && d.bonus_percent !== 60)
        return "bonus_percent must be 50 or 60";
    if (d.maturity_months !== 6) return "maturity_months must equal 6";
    var statuses = {DEPOSIT_OFFERED: "OFFERED", DEPOSIT_ACCEPTED: "ACCEPTED",
                    MATURITY_REACHED: "BONUS_READY", BONUS_ACCEPTED: "BONUS_ACCEPTED",
                    COMPLETED: "COMPLETED"};
    if (!Object.prototype.hasOwnProperty.call(statuses, d.event)) return "Unsupported event";
    if (d.status !== statuses[d.event]) return "Invalid status for event";
    var userEvent = d.event === "DEPOSIT_ACCEPTED" || d.event === "BONUS_ACCEPTED";
    if (d.actor_role !== (userEvent ? "USER" : "BANK")) return "Invalid actor_role";
    if (d.source_chain !== (userEvent ? "k269012" : "GreenAddress"))
        return "Invalid source_chain";
    var destination = userEvent || d.event === "COMPLETED" ? "GreenAddress" : "k269012";
    if (d.destination_chain !== destination) return "Invalid destination_chain";
    if (userEvent) {
        var r = d.relay_ref;
        if (!r || r.chain !== "k269012" || r.stream !== "user_events" ||
            typeof r.txid !== "string" || !/^[0-9a-f]{64}$/.test(r.txid) ||
            typeof r.payload_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(r.payload_sha256) ||
            !integer(r.vout) || r.vout < 0)
            return "Relayed user event requires a user_events transaction reference";
        // This is reference SHAPE validation, NOT verification of the other blockchain.
    }
    var bonusRequired = d.event === "MATURITY_REACHED" ||
                        d.event === "BONUS_ACCEPTED" || d.event === "COMPLETED";
    if (bonusRequired || d.bonus_amount !== undefined || d.final_amount !== undefined) {
        var expected = d.principal * d.bonus_percent / 100;
        if (!integer(expected)) return "Bonus must be representable in whole demonstration units";
        if (!integer(d.bonus_amount) || d.bonus_amount !== expected)
            return "Incorrect bonus amount";
        if (!integer(d.final_amount) || d.final_amount !== d.principal + expected)
            return "Incorrect final amount";
    }
    // No error string -> accepted. No network, sleep, state cache or wall-clock checks here.
}
