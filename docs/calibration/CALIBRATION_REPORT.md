# Calibration status

**Status: not established by the artifacts in this repository.**

An earlier version of this document reported Cohen's kappa values, scorer/human divergence percentages and certification on 200 annotations. The repository contains no corresponding annotated pairs, annotator records, sampling manifest or calculation script with which to verify those numbers. They must not be treated as measured results or a certification. The earlier text remains recoverable in Git history.

The implemented scorers are regex/word-overlap/parameter-shape heuristics and a small static fact list. Tests demonstrate deterministic software behavior, not agreement with human judgments. The upgrade adds frozen inputs, recorded recovery conversations and regression checks; it does not supply an empirical calibration study.

A future reproducible study should publish:

1. Frozen prompt IDs, exact responses and scorer source revision, with consent and appropriate data handling.
2. The sampling procedure and actual per-category counts, including duplicate-prompt treatment.
3. Independent anonymized annotations, explicit labels/rubrics and adjudication policy.
4. Calculation scripts, uncertainty intervals and disagreement analysis, including missing dimensions.
5. Separate model-quality, heuristic-validity and transport/reliability results.

Until those artifacts exist, no agreement percentages, benchmark rankings, safety guarantees or load-test SLOs are claimed.
