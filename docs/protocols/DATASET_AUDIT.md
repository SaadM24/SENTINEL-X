# Dataset audit

## Executed UNSW-NB15 intake

UNSW Canberra generated the experimental traffic in a cyber range using IXIA PerfectStorm. The original corpus combines normal activity and scripted attack behaviours. It is an external, labelled benchmark with a controlled collection environment. The investigators produced 2,540,044 records and describe a 175,341-row training partition and an 82,332-row test partition. Our copies match those row counts, field names and partition direction. Some public mirrors reverse the file names. We require the pinned bytes and reject an unexpected copy. The publisher's distribution page lists no independent SHA-256 for the CSVs we used. [Publisher, file access, feature dictionary and reuse terms](https://research.unsw.edu.au/projects/unsw-nb15-dataset)

| CSV cache location | Observed bytes | SHA-256 of retrieved copy |
|---|---:|---|
| data/raw/unsw/train.csv | 32,117,673 | afab90b86a0383f249d263e32e21795e33cdfeb906e834f55e7f1ea0fb592dbe |
| data/raw/unsw/test.csv | 15,298,464 | e4d5f673a05f2e4b93233dcb57318a15016261fc76d4547767648485703d9930 |

The importer retrieves the CSVs from a pinned public mirror. If automatic retrieval fails, save those same two files at the indicated cache paths. A different newline encoding changes the expected byte fingerprint. The prepared CSV and manifest suffice for the packaged bounded analysis. [Pinned mirror directory](https://github.com/huangxyy/bdcc-ids-defense-selection/tree/a490371076ed35c1819815c2371874a8bebeb0b1/data)

The publisher grants perpetual free academic research use, requests citations to the following five works, and directs commercial users to its authors for agreement.

1. N. Moustafa and J. Slay (2015), *UNSW-NB15: a comprehensive data set for network intrusion detection systems (UNSW-NB15 network data set)*, MilCIS. [DOI](https://doi.org/10.1109/MilCIS.2015.7348942)
2. N. Moustafa and J. Slay (2016), *The evaluation of Network Anomaly Detection Systems: Statistical analysis of the UNSW-NB15 data set and the comparison with the KDD99 data set*, Information Security Journal. [Publisher bibliography](https://research.unsw.edu.au/projects/unsw-nb15-dataset)
3. N. Moustafa et al., *Novel Geometric Area Analysis Technique for Anomaly Detection Using Trapezoidal Area Estimation on Large-Scale Networks*, IEEE Transactions on Big Data. [Publisher bibliography](https://research.unsw.edu.au/projects/unsw-nb15-dataset)
4. N. Moustafa et al. (2017), *Big Data Analytics for Intrusion Detection System: Statistical Decision-Making Using Finite Dirichlet Mixture Models*, Data Analytics and Decision Support for Cybersecurity. [Publisher bibliography](https://research.unsw.edu.au/projects/unsw-nb15-dataset)
5. M. Sarhan, S. Layeghy, N. Moustafa and M. Portmann (2021), *NetFlow Datasets for Machine Learning-Based Network Intrusion Detection Systems*. [DOI](https://doi.org/10.1007/978-3-030-72802-1_9)

### Fields and availability

Only 19 end-of-flow numeric aggregates enter this experiment. The base names and units follow the original dictionary. The processed CSV prefixes model inputs with `f_`.

| Original fields | Interpretation |
|---|---|
| dur, rate | Flow lifetime and recorded traffic rate |
| spkts, dpkts, sbytes, dbytes | Source/destination packet and byte counts |
| sload, dload | Directional load in bits per second |
| sloss, dloss | Directional packet loss/retransmission estimates |
| sinpkt, dinpkt, sjit, djit | Directional inter-packet times and jitter |
| tcprtt, synack, ackdat | TCP round-trip and handshake timing components |
| smean, dmean | Mean packet size by direction |

The training code must consume only the prefixed columns. Binary label zero denotes normal, one denotes attack. attack_category is a reporting field. event_id links to an original partition and its row ID. The source IDs do not identify hosts, sessions or absolute event times. These features describe completed flows. Early interruption of an ongoing attack was outside the measured task.

### Partition and audit results

Projection compresses distinct real flows with matching measurements into a single vector. Repeated and category-conflicting vectors can substantially bias estimates. A disk-backed SQLite primary key groups the numeric projection separately within each source. A training vector is retained or excluded using training information alone. The test pass discards every vector seen in the training source, including vectors excluded from training. Within either file, a conflict in binary label **or** attack category excludes the local vector. First source occurrence supplies the record ID. Empty numeric values are represented uniformly; there were zero missing entries across the retained feature columns in the two input files.

| Quantity | Training file | Testing file |
|---|---:|---:|
| Source rows | 175,341 | 82,332 |
| Distinct projected vectors | 88,300 | 46,034 |
| Additional occurrences of projected vectors | 87,041 | 36,298 |
| Distinct vectors with a category conflict | 884 | 343 |

1,076 distinct vectors occurred in both files, including some vectors counted in the ambiguity totals. Source labels were audited for the required normal/binary-label relationship. SHA-256 of the normalized observation assigns approximately 20% of eligible training-file vectors to calibration using an initial byte threshold of 51/256. The bounded run takes the smallest remaining hash suffixes within each resulting partition, independent of labels. It samples unique, unambiguous representations and therefore answers a different question from scoring all raw events weighted by frequency. The procedure suppresses frequent attacks such as Generic and may make performance optimistic on intrinsically ambiguous vectors.

| Split | Eligible vectors | Bounded cohort | Benign | Attack |
|---|---:|---:|---:|---:|
| Train | 70,021 | 6,000 | 3,256 | 2,744 |
| Calibration | 17,395 | 1,500 | 794 | 706 |
| Test | 44,759 | 3,000 | 2,006 | 994 |

Category-specific counts, including the small number of Worms and Analysis examples, are recorded in `data/processed/research/manifest.json`. Calibration contains zero Worms examples. The binary model only receives their shared attack label. Source collection artefacts and dependence between different vectors from the same hosts remain possible. Row IDs and file order do not support a host-disjoint or chronological interpretation.

## Other candidate datasets

The University of Queensland publishes the NF v2 series with 43 NetFlow features and a separate feature dictionary. NF-UNSW-NB15-v2 derives from UNSW traffic. NF-CSE-CIC-IDS2018-v2 derives from CSE-CIC-IDS2018 and has a different attack taxonomy. Compare these two NetFlow v2 corpora in their shared feature representation. Binary labels require source-specific verification. The native 19-column UNSW representation above is a different extractor; none of its held-out performance numbers measure cross-corpus transfer. No publisher-prescribed split was verified for these v2 downloads. They are available for academic research with attribution, with commercial reuse subject to author agreement. [UQ dataset catalogue and counts](https://staff.itee.uq.edu.au/marius/NIDS_datasets/) · [UQ reuse terms and features](https://www.cyber.uq.edu.au/project/machine-learning-based-nids-datasets) · [NF-UNSW-NB15-v2](https://rdm.uq.edu.au/files/8c6e2a00-ef9c-11ed-827d-e762de186848) · [NF-CSE-CIC-IDS2018-v2](https://rdm.uq.edu.au/files/ce5161d0-ef9c-11ed-827d-e762de186848)

## Synthetic interface fixture

`data/processed/smoke` contains 560 independent, seeded samples generated by `write_smoke`. These columns exercise the same interface. Their numerical values have no network-traffic interpretation. Fixture labels and effects were generated by design.

## Independent NetFlow v2 experiment inputs

The two compressed files were retrieved from version 1 of the **asdibnufvsd** Kaggle mirrors. The mirror metadata lists an unspecified license. Academic reuse conditions come from the original UQ publisher. Each ZIP contains one CSV with 43 original feature names plus Label and Attack. The reference byte hashes below pin the exact retrieved archives. They are independently computed hashes, with no claim of a publisher signature. The Kaggle metadata reported the same archive sizes retrieved locally. Publisher feature definitions and source-specific counts can be independently checked in the [UQ catalogue](https://staff.itee.uq.edu.au/marius/NIDS_datasets/).

| Archive | Compressed bytes | CSV bytes | SHA-256 |
|---|---:|---:|---|
| nf-unsw-nb15-v2.zip | 37,060,516 | 441,867,785 | c686c1eb7057e42d3ffff3797277804687b9780b3becb7185cb9c66811cdbf1c |
| nf-cse-cic-ids2018-v2.zip | 672,361,898 | 3,221,378,977 | ac38f3a072882f0d06395ad4ca1a6d84d2844411fdb497cd9ddd2b06ac1b9719 |

With about 750 MB of free cache space, run the commands below from the repository root. The CSVs are streamed directly from ZIP and never require their full uncompressed size on disk. Keep a new output directory per experiment.

```powershell
python scripts/download_nf_v2.py
python scripts/run_nf_shift.py --source data/raw/nf-v2/nf-unsw-nb15-v2.zip --target data/raw/nf-v2/nf-cse-cic-ids2018-v2.zip --output results/external/local-v2
```

If the API becomes unavailable, download the original ZIPs for these version-1 mirrors into the same cache directory and rerun the commands. [Source mirror](https://www.kaggle.com/datasets/asdibnufvsd/nf-unsw-nb15-v2) · [Target mirror](https://www.kaggle.com/datasets/asdibnufvsd/nf-cse-cic-ids2018-v2)

Archive download uses the network only for this public dataset and caches each successful file. No traffic capture or event generation occurs. An external logistic regression evaluation uses a uniform random priority sample from each complete file with different seeds. Duplicate and contradictory vectors are checked within the samples; feature duplicates occurring outside the sampled rows are unmeasured. The sampled source is split after deduplication. Full-corpus counts have a different denominator from the deduplicated score populations.

### Checks on the retrieved v2 archives

A second pass read every label and category in the two archives. The source contained 95,053 attack rows among 2,390,275. The target contained 2,258,141 attack rows among 18,893,708. In each source every benign category mapped to label 0 and every other category mapped to 1. These observed counts match the UQ catalogue. Original category spellings are retained in the audit.

```powershell
python scripts/audit_nf_v2.py --run results/external/local-v2 --output results/external/local-v2-audit.json
python scripts/audit_detection_data.py data/processed/research
```

The first command also recomputes 500 stratified bootstrap draws from stored predictions. Its intervals condition on the fitted model and the sampled sets. The second independently parses actual model-input CSV numbers and checks schema, class counts, record identity and exact feature-vector overlap. The release includes the audits in `results/external/nf-v2-audit.json` and `results/v01/audit/independent_cohort_audit.json`.
