# Ablation studies

| Ablation | Same evaluation unit | Observed contrast |
|---|---|---|
| Calibration on native full test | 44,759 unique flow vectors | Logistic Brier 0.23336 raw, 0.22587 Platt. Forest 0.11840 raw, 0.11937 Platt, 0.11656 temperature. |
| Training-median duration substitution | Same fitted logistic model and test vectors | AP 0.47241 to 0.47017. No inference about other feature outages. |
| Remove adjacent-call information | 3,070 ADFA test traces | AP 0.46141 with transitions, 0.31418 with independent tokens. At separately fixed thresholds, false-positive rates 17.14% and 13.93%. |
| Add transition score to calibrated syscall frequencies | 621 scenario-separated test traces | AP 0.75653 to 0.75728; retained errors 37 to 39 when 124 cases were sent to review. |
| Disable session correlation | Eight controlled investigation queries | Expected related record recovery 12/12 to 6/12. Both variants preserved nine correct field values. |
| Remove citations only | Same observations | Nine values stayed correct; cited observations decreased from nine to zero. |
| Deliberately shift reference IDs | Twenty real-flow review packet cases | Model names coincidentally matched in all 20; probabilities matched in zero. Checking the anchor rejected every wrong identity. |

Selection is also an ablation: on the full primary flow model the 20% target removed 9,830 events from the automatic pathway and reduced retained risk by 3.15 percentage points. The fixed-queue trace experiment instead holds the exact review count constant. Neither experiment measured what a human would decide.
