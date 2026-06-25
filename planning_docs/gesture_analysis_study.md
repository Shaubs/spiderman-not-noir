# Gesture Analysis Study

This document explains the analysis methodology and records the results of gesture studies.

---

## Analysis Methodology

### How Percentage Analysis Works

The analyzer calculates **consistency percentages** across all captured samples:

#### Palm Orientation Analysis
```
Palm inverted (wrist above knuckles): 95.0%
```
- Checks if `wrist.y < average_knuckle_y` for each sample
- High percentage (>80%) = reliable condition for detection

#### Finger Position Analysis
```
Index tip below wrist: 92.0%
Middle tip below wrist: 15.0%
Ring tip below wrist: 12.0%
Pinky tip below wrist: 88.0%
```
- Compares each fingertip Y position to wrist Y
- High percentage = finger consistently extended (for inverted palm)
- Low percentage = finger consistently folded

#### Finger Extension/Fold Analysis
```
Index extended (tip below PIP): 94.0%
Middle folded (tip above PIP): 89.0%
Ring folded (tip above PIP): 91.0%
Pinky extended (tip below PIP): 87.0%
```
- Measures tip position relative to PIP joint
- For inverted palm: extended = tip.y > pip.y, folded = tip.y < pip.y

### How to Interpret Results

| Percentage | Meaning | Action |
|------------|---------|--------|
| >85% | Very consistent | Use as required condition |
| 60-85% | Somewhat consistent | Use with lower threshold |
| <60% | Inconsistent | Don't rely on this condition |

### Example Raw Output

```
==================================================
GESTURE ANALYSIS RESULTS
==================================================
Samples analyzed: 20

Palm inverted (wrist above knuckles): 100.0%

--- Finger Position Analysis ---
Index tip below wrist: 95.0%
Middle tip below wrist: 10.0%
Ring tip below wrist: 15.0%
Pinky tip below wrist: 90.0%

--- Finger Extension Analysis ---
Index extended: 95.0%
Middle folded: 85.0%
Ring folded: 90.0%
Pinky extended: 88.0%

--- Suggested Thresholds ---
Index extension avg: 0.072 (use threshold: 0.04)
Pinky extension avg: 0.065 (use threshold: 0.04)
Middle fold avg: 0.048 (use threshold: 0.03)
Ring fold avg: 0.051 (use threshold: 0.03)
==================================================
```

### Deriving Detection Rules

From the output above:
1. Palm must be inverted (100% consistent)
2. Index and pinky should be extended (>85%)
3. Middle and ring should be folded (>85%)
4. Use suggested threshold values in detection code

---

## Study Results

### Study 1: Spider-Man Gesture (Inverted Palm)

**Date:** _Not yet conducted_

**Gesture Description:** 
- Palm facing camera, wrist on top, fingers pointing down
- Index and pinky extended
- Middle and ring folded
- Thumb spread outward

**Samples Captured:** _TBD_

**Raw Analysis Output:**
```
(Paste analysis output here after running)
```

**Findings:**
- _TBD_

**Thresholds Determined:**
| Condition | Threshold | Notes |
|-----------|-----------|-------|
| Palm inversion | _TBD_ | |
| Index extension | _TBD_ | |
| Pinky extension | _TBD_ | |
| Middle fold | _TBD_ | |
| Ring fold | _TBD_ | |

**Detection Code Generated:**
```python
# Paste generated code here
```

---

### Study 2: _Future Gesture_

**Date:** _Not yet conducted_

**Gesture Description:** _TBD_

**Samples Captured:** _TBD_

**Raw Analysis Output:**
```
(Paste analysis output here)
```

**Findings:** _TBD_

---

## Notes & Observations

_Record any observations about gesture detection accuracy, lighting conditions, distance variations, etc._

---

**← Back to [Gesture Detection Plan](gesture_detection_plan.md)**
