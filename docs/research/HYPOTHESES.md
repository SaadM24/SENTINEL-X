# Hypotheses and tests

| Hypothesis | Comparison | Outcome that weakens the claim |
|---|---|---|
| H1. Model families differ | Identical eligible UNSW splits, four classical and three neural model families | Similar ranking, detection or false-positive outcomes across families |
| H2. Calibration improves reliability | Compare raw and mapped scores on held-out events, primarily Brier, secondarily ECE | Worsening Brier or gains restricted to certain models |
| H3. Reviewing uncertain cases improves automatic reliability | Compare errors/accepted with all-accepted baseline; report actual escalation fraction | Risk stays level, increases, or only improves at impractical review volume |
| H4. Trace order contributes information | Fixed first-order model against token independence and paired calibrated feature fusion | No gain in AP, a higher false alarm rate at the fixed threshold, or worse calibrated decisions |
| H5. Dataset shift changes performance | Fixed detector on native source test and compatible external NetFlow test | Little change across measured metrics after accounting for base rate |
| H6. Retrieval makes analyst summaries verifiable | Compare full retrieval, anchor-only and citation-stripped cases against field-level evidence | Invalid links, missed relevant records or unchanged factual-support rates |

This is an engineering evaluation with descriptive contrasts. No family of confirmatory significance tests was registered. A method can gain on one endpoint and lose on another. The analyst-time endpoint requires a separately recruited human sample.
