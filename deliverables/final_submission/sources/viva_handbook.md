# Viva preparation and demonstration handbook

## Q1. What is the project's central question?

Whether audited flow detectors retain useful recall under leakage-aware, chronological and external evaluation at declared operating points, and whether the resulting evidence and inference can be reconstructed.

## Q2. What is the strongest defensible contribution?

An integrated, traceable evaluation with explicit cohorts, frozen thresholds, negative findings and faithful portable inference. It is not invention of Spark, random forests or a new state-of-the-art classifier.

## Q3. Why study cyberattack detection at scale?

Large heterogeneous flow collections make provenance, numerical quality, leakage and execution costs consequential. Scale alone does not make the detector operationally effective.

## Q4. What does completion mean here?

Accepted research phases, actual academic documents, reproducible sources, application checks and package integrity. It does not mean publication acceptance, institutional approval or prospective deployment success.

## Q5. How many source flows are there?

16,232,943 under the full-source inclusion rule: 13,484,708 benign and 2,748,235 attack rows.

## Q6. Why does another population contain 16,232,929 rows?

Fourteen capture-only timestamp flags distinguish the strict timestamp subset. The counts refer to different inclusion rules; they must be labeled rather than silently reconciled by deleting a number.

## Q7. Are capture labels exact prospective timestamps?

The audit distinguishes timestamp validity and capture context. Historical ordering is constrained by available evidence and does not provide a live network clock or prospective ground truth.

## Q8. Can the private dataset be shipped in the submission?

No. The package contains approved aggregates, compact parameters, synthetic inputs and source instructions. Recomputing private experiments requires separately authorized access.

## Q9. What is Apache Spark doing here?

It supplies typed distributed data operations, reusable transformations and fitted pipelines. The measured environment is a single-machine Spark setup; local worker sensitivity does not prove multi-node scaling.

## Q10. Why use typed numerical layers?

Explicit types and finite-value checks prevent silent parsing, malformed fields and invalid arithmetic from changing both eligible populations and model features.

## Q11. Why is zero-denominator handling important?

Rates can become nonfinite or undefined. The accepted feature contract defines their treatment; replacing it later changes the model input and invalidates numerical parity.

## Q12. What does training-only preprocessing prevent?

Validation or test distribution information from entering imputation, scaling or learned parameters. It is necessary for a meaningful held-out evaluation.

## Q13. Why does Spark lazy evaluation matter for timing?

Constructing a plan can do little work. A benchmark must consume a declared action and separate warm-up, materialization and caching conditions.

## Q14. Why retain source and output hashes?

They identify the exact artifact used by a claim. A hash establishes byte identity, not scientific correctness; it complements selectors, cohort rules and acceptance checks.

## Q15. What are protocols A, B and C?

A is grouped-random, B chronological and C unseen-family evaluation. They have different populations and scientific questions, so their scores are not interchangeable.

## Q16. What is predictor-duplicate leakage?

Identical predictor vectors assigned across roles can make held-out evaluation easier. Grouping or purging constrains reuse, but does not eliminate all capture dependence.

## Q17. How many rows are purged in B and C?

909,956 in B and 859,101 in C under the archived role procedure. Their retained training, validation and test counts remain separately documented.

## Q18. Does grouping establish temporal generalization?

No. Grouping reduces a leakage route but a random role assignment can still share capture composition with training. Chronological evaluation addresses a harder and different question.

## Q19. Can the protocols be averaged into a single final accuracy?

No defensible pooled headline follows from these incompatible test distributions. Report each metric with its protocol, operating rule and denominator.

## Q20. Why use a training sample?

Bounded fitting makes experiments feasible. The sampled fitting cohort must be reported separately from all eligible training-role rows and from the final evaluation population.

## Q21. How does logistic regression score a flow?

It applies its fitted linear score and sigmoid after the exact archived transform. Coefficients and feature ordering are part of the model identity.

## Q22. Why evaluate random forests?

They represent nonlinear interactions and offer a conventional ensemble baseline. Their grouped-random success does not remove the need for chronological and external tests.

## Q23. What does gradient boosting add?

Sequential fitted learners can capture nonlinear residual structure. The project treats it as an established comparator; algorithm complexity is not itself evidence of generalization.

## Q24. What does K-Means optimize?

Within-cluster squared distances under the chosen transformed feature geometry. A low objective does not mean clusters correspond to attacks or causal traffic mechanisms.

## Q25. Why is novelty distance not a probability?

Distance measures representation mismatch, without a calibrated mapping to attack frequency. Benign novelty and attacks near familiar clusters are both possible.

## Q26. How are novelty inputs transformed?

The accepted K-Means path preserves training imputation, signed-log transformation and training standardization before distance evaluation. User uploads do not refit these quantities.

## Q27. What is attack recall?

TP divided by TP plus FN on the declared attack population. A zero or undefined denominator must not be disguised as a successful zero-error result.

## Q28. What is benign false-positive rate?

FP divided by FP plus TN. It measures the fraction of benign examples alerted, rather than the fraction of alerts that are false.

## Q29. Why can accuracy be misleading?

A majority class can dominate the score. Attack recall, false-positive burden, precision and ranking metrics are needed with class counts and the operating threshold.

## Q30. Why use precision-recall analysis?

It exposes positive-class ranking behavior under imbalance. Its value depends on prevalence and implementation; it does not replace frozen-threshold decision metrics.

## Q31. How are external AUCs computed?

With 2,048 bins, step precision-recall integration and trapezoidal ROC integration. These are documented approximations rather than exact continuous-score integrals.

## Q32. What separates a score from a decision?

A threshold maps the score to an alert. Useful ranking can coexist with nearly zero attack recall at a validation-calibrated low-FPR threshold.

## Q33. Why not select the best threshold on the test set?

That uses held-out labels to optimize the reported decision rule. A new operating budget requires independent calibration and a separately declared evaluation.

## Q34. What is the key supervised negative result?

RF group-sample recall is about 0.8282 on A but about 0.0020 on B and 0.0243 on C. The harder protocols expose a substantial generalization limitation.

## Q35. Could weak chronological recall be hidden by AUC?

Yes, if only ranking is reported. The project retains both ranking and fixed operating-point errors so the limitation remains visible.

## Q36. Does the hybrid detector solve that weakness?

No. Hybrids do not consistently outperform all baselines. The selected chronological B OR-fusion policy has zero attack recall at its archived operating point.

## Q37. How does binary routing affect multiclass results?

An attack missed by the first stage does not reach family classification. Conditional family-stage accuracy must not be presented as end-to-end detection recall.

## Q38. What does open-set recognition attempt?

It distinguishes supported known families from unfamiliar observations under a declared rejection rule. It does not guarantee identification of every new attack mechanism.

## Q39. Why are hybrid and multiclass not live demo options?

Their accepted research evidence does not provide the same validated portable inference contract as LR, RF and K-Means. The app exposes the supported scope explicitly.

## Q40. What is a transaction in the pattern study?

A declared six-feature discretized item representation of a flow. Mining results depend on this representation and its bin boundaries.

## Q41. What does minimum support control?

The minimum population frequency for a retained itemset. Lowering support expands the search space and output volume, without automatically improving security relevance.

## Q42. What are the main FP-growth counts?

At support 0.05: 298 itemsets and 629 rules. At 0.01: 759 itemsets and 1,428 rules, on the full declared source population.

## Q43. Why are only 500 primary rules exported?

The export is bounded at 500 while the mined total is 629. Exported count and algorithm output count are different scope statements; 20 selected rules receive independent count checks.

## Q44. Does rule confidence establish causation?

No. It is an observed conditional association under the transaction design. Capture composition, prevalence and correlated measurements can explain the association.

## Q45. What makes a pattern emerging?

Its declared support or related frequency changes across capture populations. Without stable sampling and causal labels, emergence is descriptive rather than proof of a new attack mechanism.

## Q46. Is historical replay live streaming?

No. It processes archived observations in ordered batches. It demonstrates replay logic and measurements, not real-time packet ingestion or production monitoring.

## Q47. How many historical batches are used?

The B-role union contains 15,322,987 flows and supplies 49 batches. Forty-five windows have supported historical analysis under the declared eligibility rules.

## Q48. What is concept drift?

A change in a relevant data-generating relationship over time. A marginal feature distribution change can be a warning but is not automatically a changed attack decision concept.

## Q49. What does ADWIN's controlled result show?

It detects 24 of 27 targeted synthetic episodes with zero stationary alarms across 11,520 eligible checks. This supports that controlled benchmark, not labeled historical drift accuracy.

## Q50. Why not rank DDM 6/6 above ADWIN 24/27?

DDM targets a different error-stream episode population. The denominators and detection targets differ, so the fractions are not directly comparable rankings.

## Q51. What is the historical drift ground truth?

There is no authoritative concept-drift label set for the historical captures. The report therefore separates retrospective signals from controlled synthetic episode evaluation.

## Q52. What prevents label leakage in adaptation?

Prediction occurs before simulated label release, only permitted labels enter training, and candidates activate in a future window. Past predictions cannot be rewritten after learning their labels.

## Q53. Are label delays real operational arrivals?

No. They are simulated availability assumptions. Prospective use would require measured label arrival, adjudication quality and operational handling of missing or delayed feedback.

## Q54. What is the primary adaptive population?

1,997,636 evaluation rows. It is distinct from full-source, replay and external populations.

## Q55. How do P0 and P2 compare?

P0 has TP 463 and FP 4,691; P2 has TP 634 and FP 9,835. P2 gains recall but more than doubles the false-positive count in this primary evaluation.

## Q56. Why can retaining an incumbent be sensible?

A candidate may not meet its acceptance criteria or budget. P6 retains its incumbent and matches P0 here; rejecting an update can be the declared policy's correct behavior.

## Q57. Do 288 synthetic experiments prove broad deployment success?

No. They enumerate controlled configurations, not independent prospective environments. The 33 unique historical pipelines are also a distinct scope count.

## Q58. What does SHAP explain?

A fitted model's attribution under a specified background and link function. It does not by itself establish causal traffic effects or adversarial robustness.

## Q59. What is validated for linear SHAP?

Exact additive reconstruction in log-odds across 48 variants. Base value plus contributions reproduces the supported modeled quantity in that link space.

## Q60. Can contributions be added as probabilities?

No. Log-odds additivity is not probability additivity; the sigmoid is nonlinear. Displays must preserve the declared link-space interpretation.

## Q61. Why is direct tree SHAP unavailable?

The archived PySpark tree contract is unsupported by the validated direct interventional implementation. The report documents this limitation rather than inventing compatible explanations.

## Q62. Which external dataset is used?

A pinned version-1 CICIDS2017 Kaggle mirror with eight CSV files totaling 884,645,759 bytes. Exact official-archive byte identity and extractor builds remain unverified.

## Q63. How many external rows are eligible?

2,830,743: 2,273,097 benign and 557,646 attack rows. The primary chronological test is smaller and must use its own denominator.

## Q64. What is the primary external test denominator?

308,939 rows: 179,664 benign and 129,275 attacks. Collision exclusions are 287,528 for this protocol; grouped evaluation has a different population.

## Q65. Why only three external features?

They are conditionally compatible across the available measurements. This does not validate exact archived 18-feature transfer, which remains unsupported.

## Q66. Are source common-feature models the archived models?

No. They are newly trained three-feature baselines used by the accepted external study. Their identity and calibration differ from the archived 18-feature pipelines.

## Q67. What does source LR do externally?

At the primary validation-calibrated operating point it detects zero attacks, with zero false positives. That is a failed detection outcome despite a clean-looking false-positive count.

## Q68. How does source RF transfer?

It records 14,459 TP and 7,643 FP, recall about 0.11185 and FPR about 0.04254. Its external false-positive burden exceeds the source-validation ceiling.

## Q69. Why does target RF have two very different recalls?

The calibrated low-FPR threshold gives recall about 0.05436; fixed 0.5 gives about 0.64954 with FPR about 0.01722. The threshold changes the operating trade-off.

## Q70. Does Spark beat Pandas here?

Not on the matched measured one-million-row workload: Pandas median is 0.242245 seconds and Spark 0.616481 seconds. Broader distributed capability does not reverse this observation.

## Q71. Do four workers always improve runtime?

No. Local scheduling and overhead can outweigh parallelism. The recorded local worker sensitivity does not demonstrate multi-node speedup or production capacity.

## Q72. What is the storage comparison?

The recorded numeric Parquet artifact is 116,203,334 bytes and read median 0.626799 seconds, versus CSV 217,833,168 bytes and 1.921769 seconds for the declared workload.

## Q73. What can the dashboard actually predict?

Supported portable LR, RF and K-Means outputs under their accepted ordered 18-feature contracts. Research-only hybrid and family methods remain evidence views.

## Q74. What does the parity suite establish?

Across 2,445 accepted Spark probes, portable outputs match within recorded numerical tolerances. It proves implementation fidelity for those contracts, not new generalization accuracy.

## Q75. What are upload boundaries?

One MiB and 500 rows, exact ordered feature schema, finite nonnegative values no greater than 1e12, training-median treatment of allowed blanks, and preserved invalid-row diagnostics.

## Q76. Why isolate uploaded results from cached research evidence?

Session inputs must not mutate immutable accepted results or share user data through a global evidence cache. Uploaded predictions are demonstrations under the archived contract.

## Q77. Does the app require Kaggle or Spark at runtime?

The supported dashboard uses compact local artifacts and its own dashboard requirements. Spark, Java and Kaggle are research execution dependencies rather than app inference dependencies.

## Q78. What should be demonstrated to an examiner?

Show provenance, supported manual or synthetic CSV inference, one invalid-row diagnostic, a safe export, an appropriate explanation and the historical replay's explicit retrospective label.

## Q79. Which limitations matter most for operational use?

Weak chronological recall, false-positive costs, capture dependence, conditional external compatibility, simulated labels, unsupported tree explanations and absence of multi-node or prospective validation.

## Q80. What is the next defensible research step?

Obtain compatible provenance and prospective labels, declare operating budgets independently, and evaluate new data without test-driven tuning. Public hosting alone would not resolve scientific limitations.

## 60-second introduction

Good morning. This project evaluates large-scale cyberattack detection with explicit attention to leakage, generalization and reproducibility. It audits 16,232,943 source flows, uses Spark pipelines and evaluates supervised, novelty, pattern, drift and adaptive methods under separate protocols. The central finding is that strong grouped-random performance does not establish useful chronological detection. Hybrid and adaptive policies also show mixed results and false-positive trade-offs. External validation is limited to three conditionally compatible features, while local execution measurements do not prove multi-node scaling. The contribution is a traceable experimental system and a faithful dashboard for supported archived models. I will show the evidence, the negative findings and a bounded synthetic inference demonstration, then explain the limitations that remain before operational deployment.

## Three-minute overview

[0:00–1:00] Deliver the 60-second introduction above at a measured pace. Emphasize the distinction between scientific evidence and a working application.

[1:00–2:00] Show the architecture and leakage-splitting diagrams. The audited source population is not the same as every evaluation population. Protocol A is grouped-random, B chronological and C unseen-family. Random-forest recall is about 0.8282 on A but about 0.0020 on B and 0.0243 on C, so a single headline accuracy would hide the central limitation. Training transforms and thresholds are frozen from permitted roles. Pattern mining supplies associations, historical replay supplies retrospective signals, and controlled drift episodes supply a separate benchmark. None establishes causal historical drift.

[2:00–3:00] Present the application as a faithful demonstration rather than a new detector experiment. It supports LR, RF and K-Means and has 2,445 accepted parity probes. Adaptive P2 gains true positives but more than doubles false positives in the primary evaluation. Source RF transfers some external signal but exceeds its source FPR ceiling. On the measured one-million-row workload, Pandas is faster than Spark. Conclude that the contribution is an auditable integration with preserved limitations. Direct the examiner to the master results selectors, source hashes and final report for detailed verification.

## Five-minute demonstration

[0:00–0:40] Open the local advanced dashboard. State that its research tables are immutable archived evidence and the synthetic demo does not represent a newly evaluated dataset. Show the provenance/model identity panel.

[0:40–1:30] Open the inference area and choose LR. Load the packaged synthetic_demo.csv using the interface upload control. Explain the ordered 18-feature schema, archived medians and 500-row/1-MiB limits. Avoid private flow data.

[1:30–2:20] Inspect a valid prediction and its operating rule. Explain score versus threshold decision. Switch to RF only after confirming its model identity. Probability parity does not establish attack accuracy on these synthetic rows.

[2:20–3:00] Display the supported linear explanation. Explain base value plus contributions in log-odds and the nonlinear probability link. State that direct archived PySpark tree SHAP remains unsupported.

[3:00–3:40] Show one malformed or negative feature row and its retained diagnostic. Export the safe result and confirm invalid rows are distinguishable. Do not change the schema or fit transforms on the upload.

[3:40–4:20] Open the K-Means result or manual input. Explain transformed distance and why it is not an attack probability. Relate this to the novelty study's calibration boundary.

[4:20–5:00] Open historical replay and its retrospective disclaimer. Finish at the protocol evidence view and identify weak chronological recall and mixed adaptation trade-offs. If a service is unavailable, use the packaged genuine screenshots and accepted receipts, explicitly describing them as recorded evidence rather than a live action.

## Ten-minute defense script

[0:00–1:00] Deliver the 60-second introduction. Identify the population, generalization question and evidence-led contribution.

[1:00–2:00] Explain the source audit and Spark engineering using the dataset and data-engineering slides. Distinguish malformed input handling, strict timestamp eligibility and training-only transforms. Describe materialized actions rather than lazy-plan timing.

[2:00–3:00] Show role assignment and leakage purging. Explain protocols A, B and C, their different denominators, and why grouped-random recall cannot establish future-capture performance. Give the RF contrast and preserve its operating-point context.

[3:00–4:00] Explain hybrid and open-set limitations. A family-stage model cannot recover a binary miss. Novelty is distance in a chosen representation. The selected B hybrid policy has zero attack recall; present this openly as a negative result.

[4:00–5:00] Cover pattern mining and drift. Give the support-0.05 itemset/rule counts and bounded export. Explain capture-composition confounding. Separate ADWIN's controlled 24/27 result from the absence of historical concept-drift ground truth.

[5:00–6:00] Explain delayed-label adaptation. Present P0 and P2 true/false positives on the 1,997,636-row population and P6 incumbent retention. Describe future-only activation and why simulated label availability is narrower than operational online learning.

[6:00–7:00] Explain supported linear SHAP and conditional external validation. The external primary test has 308,939 rows; three compatible features do not establish exact 18-feature transfer. Source LR detects no attacks, while source RF exceeds its source-calibrated FPR budget.

[7:00–8:00] Present workload-specific execution findings. Pandas is faster on the matched one-million-row workload; four local workers are not consistently faster. Parquet reduces measured storage and read costs. These results do not establish multi-node scalability.

[8:00–9:00] Demonstrate a supported manual prediction or the packaged synthetic CSV. Inspect model identity and an invalid-row diagnostic. Explain portable parity, session isolation and the research-only scope of unsupported methods.

[9:00–10:00] Summarize the integrated contribution, remaining limitations and reproducibility package. Point to report, manuscript, master-results selectors and hashes. Future work requires prospective labels, compatible provenance and independent operating budgets. Invite questions without claiming publication acceptance or public deployment.

## Final demonstration checklist

- Replace student, registration, institution, supervisor, date and manuscript email placeholders.
- Review the report and manuscript against the actual university and venue templates.
- Start dashboard/advanced_app.py from the repository root using dashboard requirements.
- Use only packaged synthetic_demo.csv for the demonstration; confirm model identity and input bounds.
- Keep report, manuscript, slides, speaker notes and evidence tables open locally.
- Confirm the CSV export location and use safe diagnostic rows.
- Explain that replay is historical and labels in adaptation are simulated.
- Retain genuine screenshots as an explicitly labeled fallback.
- Rehearse timed scripts aloud; timings are pacing targets, not measured narration durations.
- Check the final ZIP checksum and protected-reference receipt.
- Perform any public deployment separately; none is included in this submission task.

## Quick revision card

Source 16,232,943; replay 15,322,987; adaptive 1,997,636; external primary test 308,939. RF A recall 0.8282; B about 0.0020; C about 0.0243. Source external RF recall 0.11185 / FPR 0.04254. P0 TP/FP 463/4691; P2 634/9835. ADWIN 24/27 controlled episodes. Pandas/Spark one-million-row medians 0.242/0.616 seconds. Portable parity 2,445 probes. Never pool these denominators or describe historical replay as live monitoring.
