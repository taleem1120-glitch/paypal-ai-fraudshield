import {parseReceipt} from "./receipt.mjs";

export async function lookupReceipts(invoke, caseId) {
  const id = caseId.trim().toLowerCase();
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(id))
    throw Error("Enter a valid case UUID.");
  const res = await invoke({path: "/forge/cases/" + id + "/receipts", method: "GET"});
  if (res?.status !== 200 || !Array.isArray(res.body?.receipts) || res.body.receipts.length > 20)
    throw Error("Lookup unavailable. Check your account and case access.");
  return res.body.receipts.map(item => {
    const receipt = parseReceipt(JSON.stringify(item));
    if (receipt.case_id !== id) throw Error("Case mismatch.");
    return receipt;
  });
}

export async function verifyStored(invoke, receipt) {
  const ref = parseReceipt(JSON.stringify(receipt));
  const path = "/forge/cases/" + ref.case_id + "/receipts/" + ref.sha256 + "/verify";
  const res = await invoke({path, method:"POST"});
  if (res?.status === 409) throw Error("Integrity check failed. Review the original in FraudShield.");
  const body = res?.body;
  if (res?.status !== 200 || body?.verified !== true || body.case_id !== ref.case_id ||
      body.sha256 !== ref.sha256 || typeof body.checked_at !== "string" ||
      !Number.isFinite(Date.parse(body.checked_at)))
    throw Error("Verification unavailable. Check access and retry.");
  return body.checked_at;
}
