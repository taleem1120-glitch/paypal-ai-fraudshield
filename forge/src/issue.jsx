import React, {useEffect, useState} from "react";
import ForgeReconciler, {Button, Text, TextArea, useProductContext} from "@forge/react";
import {requestJira} from "@forge/bridge";
import {issueReceipt} from "./receipt.mjs";

function Issue() {
  const context = useProductContext();
  const id = context?.extension?.issue?.id;
  const [input, setInput] = useState("");
  const [receipt, setReceipt] = useState(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(true);
  useEffect(() => {
    let active = true;
    if (id) issueReceipt(requestJira, id).then(value => active && setReceipt(value))
      .catch(() => active && setMessage("Could not read receipt."))
      .finally(() => active && setBusy(false));
    return () => {active = false;};
  }, [id]);
  async function save() {
    setBusy(true);
    try {
      setReceipt(await issueReceipt(requestJira, id, input));
      setInput("");
      setMessage("Receipt saved.");
    } catch {
      setMessage("Check the receipt and your issue-edit permission.");
    } finally { setBusy(false); }
  }
  return <>
    <Text>{receipt ? "Case " + receipt.case_id + " · SHA-256 " + receipt.sha256 : "No receipt displayed."}</Text>
    <Text>Paste the case receipt. Saving replaces the reference visible to issue readers.</Text>
    <TextArea value={input} onChange={event => setInput(event.target.value)} />
    <Button isDisabled={busy || !id || !input} onClick={save}>Save receipt</Button>
    <Text>{message}</Text>
  </>;
}
ForgeReconciler.render(<Issue />);
