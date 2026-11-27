# Enterprise risk policy diagnostic gate

Run `python -m enterprise_core.policy_diagnostics` in the locked enterprise environment. The deterministic grid exercises six amount boundaries, three currencies and all 27 combinations of present/missing indicators (486 cases). The expected contract is 48 scored cases and 438 abstentions. The test asserts exact rule scores, risk bands, abstention reasons and repeatability. These expected results are a contract specification until the candidate CI succeeds.

The grid validates rule implementation, not fraud detection accuracy, false-positive rate or business value. It contains no real or labeled transactions. Do not use it to tune thresholds for production. A representative authorized, time-separated labeled dataset and a buyer-defined review-cost objective are required before evaluating precision, recall, false positives, or threshold changes. The existing synthetic anomaly model is not a calibrated probability of fraud. No payment blocking is performed.

The gate preserves the existing manual-usd-v1 policy and receipt format.
