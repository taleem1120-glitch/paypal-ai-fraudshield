const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
export function parseReceipt(text) {
  if (typeof text !== "string" || text.length > 512) throw Error("Invalid receipt.");
  const value = JSON.parse(text);
  if (!value || Object.keys(value).sort().join(",") !== "case_id,schema,sha256" ||
      value.schema !== "fraudshield-receipt-v1" || typeof value.case_id !== "string" ||
      typeof value.sha256 !== "string" || !uuid.test(value.case_id) ||
      !/^[a-f0-9]{64}$/.test(value.sha256)) throw Error("Invalid receipt.");
  return {schema: value.schema, case_id: value.case_id, sha256: value.sha256};
}
export async function issueReceipt(request, id, input) {
  if (!/^\d+$/.test(String(id))) throw Error("Issue unavailable.");
  const url = "/rest/api/3/issue/" + id + "/properties/fraudshield.receipt.v1";
  if (input !== undefined) {
    const receipt = parseReceipt(input);
    const response = await request(url, {method: "PUT", headers: {"Content-Type": "application/json"},
                                         body: JSON.stringify(receipt)});
    if (!response.ok) throw Error("Could not save receipt.");
    return receipt;
  }
  const response = await request(url);
  if (response.status === 404) return null;
  if (!response.ok) throw Error("Cannot read receipt.");
  return parseReceipt(JSON.stringify((await response.json()).value));
}
