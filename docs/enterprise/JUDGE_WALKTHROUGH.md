# FraudShield Enterprise X

## Submission copy

Finance investigators need to answer a simple question when a disputed checkout changes hands. Can the next reviewer retrieve the same original that the first investigator saw?

FraudShield preserves the original assessment with its case and records the custody event. An investigator links a compact receipt to the Jira issue. A second authorized investigator can reopen the issue and ask the remote service to hash the retained bytes again. A Confluence page can carry the same receipt for a report. The original stays in the organization's case store. A digest match establishes byte continuity. The analyst remains responsible for the fraud decision.

The Forge issue panel uses Jira issue properties and invokes a tenant-bound verification service. The Confluence UI Kit macro presents a reference entered by a page editor. The enterprise workbench also previews incomplete USD transactions, showing the possible rule-score range and requesting manual review. Unsupported currencies remain unscored.

**Category** · Apps for Business Teams. **Audience** · Finance operations and investigation leads who already coordinate cases in Jira.

## Judge exercise after installation

1. The operator provisions a dedicated synthetic tenant, deploys the HTTPS service and configures the app, environment, installation and account mappings. Follow [pilot setup](PILOT.md) and [Forge verification](FORGE_VERIFICATION.md). Use the operator-issued installation link on a Jira and Confluence test site. Confirm each product installation's signed identity against the service configuration before testing.
2. As a mapped investigator with Jira edit permission, open the FraudShield evidence panel on an empty issue. Choose **Open synthetic pilot case**, then **Verify and link**. Save the displayed case ID and digest.
3. Reload the issue. Select **Verify linked evidence**. Compare the server time and digest with the custody timeline in Enterprise cases.
4. Copy **Receipt for the Confluence report**. Insert **FraudShield evidence report** into a test page and paste the JSON into the macro configuration. Publish and compare both identifiers. Page readers can read the identifiers. The macro does not perform a fresh verification.
5. With a second unmapped account, verify that checking the original is denied. With a mapped viewer, confirm that reading the issue alone does not grant original-file access.
6. In Enterprise cases, preview a USD 1,850 transaction with unknown indicators. Complete all three indicators and compare the result. Upload an exported synthetic audit, then download its verified original and compare bytes.

## Commercial pilot offer

Run a paired handoff exercise with a finance operations lead and two investigators on fictional cases. Alternate which workflow goes first. Compare Jira attachments and issue history with the FraudShield receipt workflow on the same cases. Record median time to locate and check the original, failed handoffs, discrepancies detected and the number of cases requiring manual review. Ask the buyer to set acceptable limits before the pilot. Pilot scope covers integration, investigator training and verification of restore procedures. Pricing and customer acceptance are open.

| Existing workflow | What the buyer can already do | What to test in a FraudShield pilot |
| --- | --- | --- |
| Jira attachments and issue history | Attach supporting files and see changes to a work item | Whether in-issue re-verification saves time while keeping originals in the case store |
| PayPal Fraud Protection Advanced review | Review triggered filters, scores and flagged payments | Whether a second investigator can reproduce an evidence handoff across teams |
| Manual digest and case register | Compare a file to a separately retained digest | Time and custody-record completeness when the original and reviewer move through the case service |

[Atlassian attachments](https://support.atlassian.com/jira-software-cloud/docs/add-an-attachment-to-an-issue/) · [Jira history](https://support.atlassian.com/jira-software-cloud/docs/what-are-the-different-types-of-activity-on-an-issue) · [PayPal review](https://developer.paypal.com/docs/multiparty/checkout/advanced/customize/fraud-protection/fraud-protection-advanced/review/)

## Final English recording

Open with the disputed checkout and the question above. Show the actual Jira panel creating the pilot, a second investigator verifying it, the custody timeline, the Confluence reference and a denied access attempt. End with the buyer's pilot measure. Record only synthetic data on the installed app. Keep the public YouTube demonstration under five minutes. The local workbench footage covers only the enterprise portion. Complete the [submission gates](CODEGEIST_2026.md) before publication.
