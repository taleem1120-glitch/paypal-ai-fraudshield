import test from "node:test";
import assert from "node:assert/strict";
import {issueReceipt, parseReceipt} from "../src/receipt.mjs";
const receipt = {schema:"fraudshield-receipt-v1",case_id:"12345678-1234-1234-1234-123456789abc",sha256:"a".repeat(64)};
test("save, retry and read use one issue property", async () => {
  const properties = new Map();
  async function request(url, options) {
    if (options) properties.set(url, JSON.parse(options.body));
    return {ok:true,json:async () => ({value:properties.get(url)})};
  }
  for (let i=0;i<2;i++) await issueReceipt(request, 42, JSON.stringify(receipt));
  assert.equal(properties.size,1);
  assert.deepEqual(await issueReceipt(request,42),receipt);
});
test("forbidden and missing responses", async () => {
  assert.equal(await issueReceipt(async () => ({status:404}),1),null);
  await assert.rejects(issueReceipt(async () => ({status:403}),1,JSON.stringify(receipt)));
});
test("reject whole reports, extra fields, oversized input and invalid IDs", async () => {
  for (const v of [{...receipt, actor:"private"}, {...receipt, sha256:"x"}, {}, null]) {
    assert.throws(() => parseReceipt(JSON.stringify(v)));
  }
  assert.throws(() => parseReceipt(" ".repeat(513)));
  await assert.rejects(issueReceipt(null,"1/other"));
});
