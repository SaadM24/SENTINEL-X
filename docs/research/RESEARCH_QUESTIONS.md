# Research questions

When should a detector make an automatic decision, and when should an analyst inspect the evidence? A high ranking score can coexist with too many false alarms for an analyst to handle. Our primary outputs are therefore a probability, a review decision and a record of which observations support the accompanying report.

1. On distinct completed flows from the UNSW benchmark, how do model family and calibration affect ranking, thresholded predictions and probability quality?
2. How many errors remain among automatically decided cases at a specified review budget? Does that budget transfer from calibration to test?
3. Does transition information add discriminatory value over event frequencies for entire Linux traces? Can it add value to a calibrated classifier tested on separate attack runs?
4. What happens to a frozen detector when the collector, attack prevalence and traffic population change?
5. Which report claims and timeline entries can a reviewer check directly? Does a case merit investigation even when the records are insufficient to infer cause?

Units differ: a network flow, a process trace and an analyst case. The independent data sources have no common incident IDs. The experiments therefore cannot establish how frequently a host anomaly explains a network alert.
