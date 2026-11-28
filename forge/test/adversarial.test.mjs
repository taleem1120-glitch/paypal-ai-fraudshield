import test from "node:test";
import assert from "node:assert/strict";
import {parseReceipt, issueReceipt} from "../src/receipt.mjs";
import {lookupReceipts, verifyStored} from "../src/verification.mjs";

const receipt = {schema:"fraudshield-receipt-v1", case_id:"12345678-1234-1234-1234-123456789abc",sha256:"a".repeat(64)};

test("invalid receipt yields a controlled error", () => {
  for (const value of ["{", "null", "[]", JSON.stringify({...receipt,extra:true})])
    assert.throws(() => parseReceipt(value), /Invalid receipt/);
});

test("duplicate or mismatched remote receipts fail closed", async () => {
  await assert.rejects(lookupReceipts(async () => ({status:200,body:{receipts:[receipt,receipt]}}),receipt.case_id),/Duplicate/);
  await assert.rejects(lookupReceipts(async () => ({status:200,body:{receipts:[{...receipt,case_id:"87654321-1234-1234-1234-123456789abc"}]}}),receipt.case_id),/Case mismatch/);
});

test("remote verification rejects integrity errors and mismatched digest", async () => {
  await assert.rejects(verifyStored(async () => ({status:409}),receipt),/Integrity check failed/);
  await assert.rejects(verifyStored(async () => ({status:200,body:{...receipt,sha256:"b".repeat(64),verified:true,checked_at:"2026-11-28T00:00:00Z"}}),receipt),/Verification unavailable/);
});

test("failed Jira write is not reported as saved", async () => {
  await assert.rejects(issueReceipt(async () => ({ok:false,status:403}),"123",JSON.stringify(receipt)),/Could not save/);
});
