// Local unit tests only. Native MultiChain V8/API evidence is separately in results/.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const code = fs.readFileSync(path.join(root, 'bank_filter.js'), 'utf8');
const valid = JSON.parse(fs.readFileSync(path.join(root, 'examples', 'valid.json'), 'utf8'));
function run(changes, expected, remove) {
  const payload = {...valid, ...changes};
  if (remove) delete payload[remove];
  const context = vm.createContext({getfilterstreamitem: () => ({keys: [payload.offer_id], data: {json: payload}})});
  vm.runInContext(code, context);
  const result = context.filterstreamitem();
  if (expected) assert.ok(typeof result === 'string' && result.includes(expected), String(result));
  else assert.equal(result, undefined);
}
run({}, null);
run({bonus_percent: 60, bonus_amount: 600, final_amount: 1600}, null);
run({bonus_amount: 400, final_amount: 1400}, 'Incorrect bonus amount');
run({final_amount: 1400}, 'Incorrect final amount');
run({}, 'Missing required field: principal', 'principal');
run({principal: 0}, 'Principal');
run({principal: true}, 'Principal');
run({bonus_percent: 55}, 'bonus_percent');
run({maturity_months: 5}, 'maturity_months');
run({user_id: 'someone_else'}, 'user_id');
run({event: 'UNKNOWN'}, 'Unsupported event');
run({status: 'OFFERED'}, 'Invalid status');
run({source_chain: 'chain1'}, 'source_chain');
run({destination_chain: 'k269012'}, 'destination_chain');
run({actor_role: 'USER'}, 'actor_role');
run({event: 'BONUS_ACCEPTED', status: 'BONUS_ACCEPTED', actor_role: 'USER',
     source_chain: 'k269012'}, 'transaction reference');
console.log('16 filter unit tests passed (Node vm, not a chain simulation).');
