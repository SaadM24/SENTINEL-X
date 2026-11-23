# Behavioural anomaly detection and supervised fusion

We evaluated genuine ordered syscall traces, preserving file boundaries throughout. A fixed first-order Markov model estimates conditional next-token probabilities from benign trace transitions. A unigram model removes previous-token information. Both assign probability to previously unseen tokens and include end-of-trace. Their scores are density estimates: a surprising transition need not be malicious. The smallest possible observation unit is an integer syscall token; an index in a file is not a timestamp.

## ADFA-LD provenance

G. Creech and J. Hu introduced this corpus in *Generation of a new IDS test dataset: Time to retire the KDD collection* (IEEE WCNC, 2013, pp. 4487–4492). The [custodian dataset page](https://research.unsw.edu.au/projects/adfa-ids-datasets) describes the host-based collection. The pinned [mirror and repackaging declaration](https://github.com/verazuo/a-labelled-version-of-the-ADFA-LD-dataset/tree/68bedf561f7b7abe9954a3ddc22dbf24c0d42372) includes an extra syscall-name mapping, which we did not use. The analysis uses numeric traces and collection directories. No explicit redistribution permission was verified for the trace collection, so the release distributes the importer, manifests and derived model/results. Mirror byte reproducibility is verified against SHA-256; correspondence to a custodian-signed hash remains unverified. ZIP size is 2,381,193 bytes, expanded member size total 8,756,422 bytes. Accessed 20 November 2026.

Hofmeyr, Forrest and Somayaji, *Intrusion detection using sequences of system calls* (Journal of Computer Security, 1998, [DOI](https://doi.org/10.3233/JCS-980109)), motivated short-range sequence modelling. Verwer and Hammerschmidt's [FlexFringe](https://lmcs.episciences.org/16573) describes interpretable probabilistic automata via state merging. Here the previous token fixes the state; there is no learned state-merging algorithm. The learned edge CSV states actual counts and row-smoothed probabilities. Missing edges receive positive probability, so displayed observed edges alone can sum to less than one. Scores can be inspected via the highest-surprise edge, its zero-based target index, and the identifiers in scores.csv; end-marker index equals trace length.

## Measured experiments

| Held-out trace comparison | Test AP | ROC-AUC | Alert recall | Benign FPR |
|---|---:|---:|---:|---:|
| Benign unigram | .3142 | .5984 | .2178 | .1393 |
| Benign first-order Markov | .4614 | .6990 | .4507 | .1714 |

The primary evaluation retained 624 training, 156 calibration and 3,070 test traces, with 730 attack-directory positives. Five percent was the nominal benign calibration tail. The test benign alarm rates of 13.9% and 17.1% demonstrate threshold instability. The Markov model raised an additional 75 false alarms while retrieving 170 additional positives. Family-specific Markov recall ranged from 30.6% (Java_Meterpreter, n=121) to 54.0% (Hydra_FTP, n=161). The primary comparison measures order sensitivity in density estimates. It does not measure an end-to-end analyst benefit.

| Exploratory supervised comparison, different split | Test AP | Calibrated Brier | Accepted errors at 124 reviews |
|---|---:|---:|---:|
| Token frequencies | .7565 | .09780 | 37 / 497 |
| Token frequencies plus Markov surprise | .7573 | .09799 | 39 / 497 |

The separate fusion experiment used 780 benign density-fit traces, then 1,832 supervised-fit, 608 calibration and 621 test traces. Its 153 test positives came from attack directories held out as entire scenarios. Exact trace digests were disjoint throughout. Adding the Markov feature left AP nearly unchanged and increased accepted errors by two. Both classifiers had lower Brier before sigmoid calibration. Little incremental evidence supports the combined approach on this split. Changes of this size should not be treated as reliable advantages. These analyses share a corpus and have different training-label access. Their raw performance numbers do not support a cross-experiment model ranking.

Original attack directory labels mark scenario membership. Some processes may execute ordinary system calls within those scenarios. No per-event attack adjudication, independent site, future host collection, unknown-family holdout or timed human study was available. For benign records, exact overlap control cannot establish host/session independence. No synthetic trace is used in the ADFA experiments.

## Reproduction

From the repository root after installation, run:

```powershell
python -m sentinel_x.behaviour --dataset adfa --out runs/my_sequence
python -m sentinel_x.fusion --out runs/my_fusion
python scripts/verify_sequence.py --sequence runs/my_sequence --fusion runs/my_fusion
python -m sentinel_x.behaviour --dataset fixture --out runs/my_fixture
```

Both real runs accept `--archive PATH` for offline input (exact pinned ZIP). Keep archive at `data/raw/ADFA-LD.zip` for automatic caching. An interrupted nonempty partial directory is preserved: pass a fresh output directory to recompute this short stage. Completed runs verify their recorded output hashes before skipping. The two frozen protocols and split manifests define all decision rules.

## Integrity checks and acquisition notes

The archive's original publication page returned HTTP 200. Two guessed historical direct-file paths on the UNSW site returned HTTP 401; neither was treated as an authoritative download or a checksum reference. The original publication page's Linux link points to an older CloudStor address. We used the named public mirror above for retrieval and pinned its ZIP digest. A separate peer-reviewed archive signature was unavailable.

The verification script recomputed the primary comparison's AP and confusion matrices from all 3,070 retained paired scores. For the follow-up it recomputed AP, Brier, confusion, and fixed-budget accepted error from 621 paired scores and checked scenario disjointness. On a fresh same-environment rerun, all derived files listed by both manifests were byte-identical. Runtime metadata naturally varied. See `reports/sequence/verification.txt` and `repeat.json`. Six unit/integration checks cover trace boundaries, smoothing, order removal, unknown tokens, overlaps, retained artifacts and scenario grouping. Score-curve rendering is reproducible via `python scripts/plot_sequence.py`.
