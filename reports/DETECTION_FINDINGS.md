# Intrusion detection and alert reliability

The complete eligible UNSW-NB15 benchmark contained 70,021 training vectors, 17,395 calibration vectors, and 44,759 test vectors under the declared 19-feature projection and ambiguity exclusion. These are unique projected observations in a laboratory collection. Natural operational alert rates cannot be estimated from them. Source classes and source split were preserved with train-side overlap priority. Duplicate removal changes the frequency of repetitive traffic. See the data manifest for original counts. The test attack fraction was 14,710/44,759 (32.87%). No host or time identity was inferred from row order.

## Comparison on all eligible test observations

| Uncalibrated model | Macro-F1 | Average precision | False alarms per 1,000 benign |
|---|---:|---:|---:|
| Logistic | .6705 | .4724 | 446.7 |
| Random forest | .8003 | .9117 | 258.1 |
| Histogram boosting | .7816 | .9177 | 294.3 |
| Isolation forest | .5052 | .4124 | 607.2 |
| Multilayer perceptron | .7594 | .8696 | 329.2 |
| Autoencoder | .5662 | .5233 | 553.6 |
| Radial basis classifier | .6894 | .5508 | 422.1 |

At the fixed 0.5 operating point the forest found 13,846 of 14,710 attacks and incorrectly flagged 7,755 of 30,049 benign records. Its precision was .6410. The neural classifier and reconstructor hit their fixed epoch budgets before the optimizer's convergence criterion. Anomaly baselines use training-benign score percentiles; the raw 0.5 point is a median-like cutoff, not a defensible production alarm policy. The experiment compares frozen configurations, not each model family's attainable optimum.

## Probabilities, escalation and shift

Platt scaling moved logistic Brier score from .23336 to .22587 and ten-bin ECE from .19168 to .17206. Logistic average precision stayed .47241. Forest Brier moved from .11840 to .11937 under Platt and to .11656 under temperature scaling. These differences demonstrate method dependence. Selecting a calibrator from these held-out comparisons would require a new evaluation.

For the prespecified logistic + Platt operating model, the error rate without abstention was .3270. A nominal 20% review target on calibration scores escalated 9,830 of 44,759 test records (21.96%). Error among retained events fell to .2955. At the 50% target it reached .2322 with 53.15% escalated. The Wilson interval for the initial error was [.3227,.3314] under an independent-record approximation. Dependence within the capture can make the interval too narrow. These budgets measure numbers of records, never analyst minutes or post-review correctness.

Replacing duration with its training median moved average precision .47241 to .47017. This single simulated outage offers little evidence about other networks. No externally collected flow dataset was transferred through this model.

## Errors and model explanations

The operating model missed 875 of 6,985 Exploits, 397 of 3,732 Fuzzers and 10 of 57 Backdoor records. Unequal denominators matter. The largest single-column permutation losses in AP were .08161 for f_ackdat and .06988 for f_tcprtt. Correlation between timing measurements complicates interpretation. The decomposition of the raw logistic score showed a mean contribution of +5.77 from f_dload for benign false positives and −7.00 for true negatives. Contributions for f_tcprtt moved in the opposite direction between these groups. The full group-wise table and the permutation table are descriptive model explanations. They identify neither attack mechanisms nor actions for real networks.

## Reproducibility and sensitivity

The three bounded runs used identical 6,000/1,500/3,000 partitions and seeds 17, 42, and 71. Across the three seeds raw forest macro-F1 ranged from .7762 to .7805, MLP from .7179 to .7224, and Isolation Forest from .5043 to .5273. These ranges measure training-seed variability only. The bounded and full runs share data and cannot be treated as independent replications.

Raw projected feature-vector overlap across splits is zero. A post-hoc audit found that training-fitted clipping, scaling and float32 storage introduced 62 test observations whose transformed feature vectors matched train or calibration. Excluding them retained 44,697 test events. Logistic + Platt macro-F1 shifted from .67008 to .66970 and AP from .472409 to .472417. Keep this sensitivity separate from the predeclared analysis.

The initial environment lacked pytest. Its cached wheel installed successfully. Fifteen detection-specific unit cases passed. Replaying all checkpoint/calibrator combinations across the five runs reproduced confusion counts, Brier scores, primary prediction IDs/probabilities, and coverage/workload arithmetic in 140/140 combinations. This is an internal executable consistency check, not independent replication or human adjudication. CUDA is optional and unexecuted.

## Reproduction

From the project root after installation, use:

```powershell
python -m sentinel_x.detection --input data/processed/research-full/events.csv --run my-full --mode research
python scripts/audit_detection.py --input data/processed/research-full/events.csv --results results/v02/my-full
python scripts/audit_transformed_overlap.py --input data/processed/research-full/events.csv --results results/v02/my-full
```

Supply --resume to reload verified completed model checkpoints. Run from the repository root. Training occurs one model at a time. Only load checkpoints you trust. The software stores fit times and batched prediction timings. An end-to-end production latency distribution was outside the measurements.
