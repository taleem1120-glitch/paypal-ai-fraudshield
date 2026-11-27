import test from "node:test";
import assert from "node:assert/strict";
import {lookupReceipts, verifyStored} from "../src/verification.mjs";
const receipt = {schema:"fraudshield-receipt-v1",case_id:"12345678-1234-1234-1234-123456789abc",sha256:"a".repeat(64)};
const time = "2026-11-27T10:00:00Z";
test("lookup limits references to the requested case", async () => {
  const result = await lookupReceipts(async () => ({status:200,body:{receipts:[receipt]}}),receipt.case_id);
  assert.deepEqual(result,[receipt]);
  await assert.rejects(lookupReceipts(async () => ({status:200,body:{receipts:[receipt]}}),receipt.case_id.replace("1","2")));
});
test("verify binds success to the exact original and server timestamp", async () => {
  const body = {...receipt, verified:true, checked_at:time};
  assert.equal(await verifyStored(async () => ({status:200,body}),receipt),time);
  for (const change of [{verified:false},{sha256:"b".repeat(64)},{case_id:"other"},{checked_at:"invalid"}])
    await assert.rejects(verifyStored(async () => ({status:200,body:{...body,...change}}),receipt));
});
test("denial, mismatch and network failure never display verification", async () => {
  for (const status of [401,403,404,409,503])
    await assert.rejects(verifyStored(async () => ({status}),receipt));
  await assert.rejects(verifyStored(async () => { throw Error("offline"); },receipt));
});
