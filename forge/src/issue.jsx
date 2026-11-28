import React, {useEffect, useState} from "react";
import ForgeReconciler, {Button, Label, Text, TextArea, useProductContext} from "@forge/react";
import {invokeRemote, requestJira} from "@forge/bridge";
import {issueReceipt, parseReceipt} from "./receipt.mjs";
import {lookupReceipts, verifyStored} from "./verification.mjs";

function Panel({id}) {
  const [input, setInput] = useState("");
  const [linked, setLinked] = useState(null);
  const [choices, setChoices] = useState([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(true);
  useEffect(() => {
    let active = true;
    issueReceipt(requestJira, id).then(value => active && setLinked(value))
      .catch(() => active && setMessage("Cannot read this issue's receipt."))
      .finally(() => active && setBusy(false));
    return () => {active = false;};
  }, [id]);

  async function run(action) {
    setBusy(true);
    setMessage("");
    try { await action(); }
    catch (error) { setMessage(error.message || "Request failed."); }
    finally { setBusy(false); }
  }
  async function lookup() {
    setChoices([]);
    const found = input.trim().startsWith("{") ? [parseReceipt(input.trim())]
      : await lookupReceipts(invokeRemote, input);
    setChoices(found);
    if (!found.length) setMessage("No accessible evidence found.");
  }
  async function link(receipt) {
    const time = await verifyStored(invokeRemote, receipt);
    await issueReceipt(requestJira, id, JSON.stringify(receipt));
    const saved = await issueReceipt(requestJira, id);
    setLinked(saved);
    if (!saved || saved.case_id !== receipt.case_id || saved.sha256 !== receipt.sha256)
      throw Error("The issue reference changed during saving. Review the current link.");
    setChoices([]);
    setMessage("Linked. Original bytes verified at " + time);
  }
  return <>
    <Text>{linked ? "Linked case " + linked.case_id + " · SHA-256 " + linked.sha256 : "No linked receipt displayed."}</Text>
    {linked && <>
      <Label labelFor="saved-receipt">Receipt for the Confluence report</Label>
      <TextArea id="saved-receipt" isReadOnly value={JSON.stringify(linked)} />
    </>}
    {linked && <Button isDisabled={busy} onClick={() => run(async () => {
      const current = await issueReceipt(requestJira, id);
      setLinked(current);
      if (!current || current.case_id !== linked.case_id || current.sha256 !== linked.sha256)
        throw Error("The issue reference changed. Review the updated link.");
      const time = await verifyStored(invokeRemote, current);
      setMessage("Original bytes matched this issue receipt at " + time);
    })}>Verify linked evidence</Button>}
    {!linked && <Button isDisabled={busy} onClick={() => run(async () => {
      setChoices([]);
      const result = await invokeRemote({path: "/forge/cases/pilot", method: "POST"});
      if (result.status !== 200) throw Error("Sample unavailable. Use a configured pilot tenant and investigator account.");
      const sample = parseReceipt(JSON.stringify(result.body));
      setInput(sample.case_id);
      setChoices([sample]);
      setMessage("Synthetic checkout case prepared. Verify its original to link it to this issue.");
    })}>Open synthetic pilot case</Button>}
    <Text>Enter a FraudShield case UUID to find its latest 20 items, or paste an exact receipt. Linking replaces this issue's visible reference.</Text>
    <Label labelFor="evidence-input">Case UUID or receipt JSON</Label>
    <TextArea id="evidence-input" value={input} isDisabled={busy} onChange={event => {setInput(event.target.value); setChoices([]);}} />
    <Button isDisabled={busy || !input.trim()} onClick={() => run(lookup)}>Find evidence</Button>
    {choices.map(item => <React.Fragment key={item.sha256}>
      <Text>{item.sha256}</Text>
      <Button isDisabled={busy} onClick={() => run(() => link(item))}>Verify and link</Button>
    </React.Fragment>)}
    <Text>{busy ? "Working… Please keep this panel open." : message}</Text>
    <Text>Verification confirms stored bytes match the digest, not the authenticity of the source or a fraud verdict.</Text>
  </>;
}
function Issue() {
  const id = useProductContext()?.extension?.issue?.id;
  return id ? <Panel key={id} id={id} /> : <Text>Loading issue…</Text>;
}
ForgeReconciler.render(<Issue />);
