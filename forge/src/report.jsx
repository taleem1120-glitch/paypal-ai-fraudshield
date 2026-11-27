import React from "react";
import ForgeReconciler, {Label, Text, TextArea, useConfig} from "@forge/react";
import {parseReceipt} from "./receipt.mjs";
function Report() {
  const config = useConfig();
  try {
    const receipt = parseReceipt(config?.receipt);
    return <>
      <Text>FraudShield evidence reference</Text><Text>Case {receipt.case_id}</Text>
      <Text>Original file SHA-256 {receipt.sha256}</Text>
      <Text>Operator-supplied receipt. Verify the original in FraudShield.</Text>
    </>;
  } catch { return <Text>Configure a valid FraudShield receipt for this report.</Text>; }
}
ForgeReconciler.render(<Report />);
ForgeReconciler.addConfig(<><Label labelFor="receipt">Receipt JSON (visible to page readers)</Label>
  <TextArea name="receipt" /></>);
