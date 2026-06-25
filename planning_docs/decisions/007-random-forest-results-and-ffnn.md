# ADR-007: Random Forest Results and Switch to Feed Forward Neural Network

**Date:** 2026-06-25  
**Status:** Accepted

## Context

We trained a Random Forest classifier on 1,218 positive Spider-Man gesture samples with 500 synthetic negative samples. While the model achieved 100% test accuracy on the synthetic data, real-world testing revealed significant issues with false positives.

### Random Forest Results

**Training Metrics (Misleading):**
- Cross-validation scores: [0.99, 1.0, 1.0, 1.0, 0.996]
- Mean CV accuracy: 99.76%
- Test accuracy: 100%

**Real-World Performance (Actual):**
- **False Positive Rate:** Very high
- **Loser hand gesture (index + pinky extended, but palm facing camera):** ~70% falsely detected as Spider-Man
- **Thumbs up gesture:** ~30% falsely detected as Spider-Man
- **Rock sign (index + pinky extended):** Falsely detected as Spider-Man

### Root Cause Analysis

1. **Synthetic negatives were insufficient:** Random noise/permutations don't capture real hand configurations
2. **Feature overlap:** The loser sign and rock sign share the same finger extension pattern (index + pinky) as Spider-Man
3. **Palm orientation features were weak:** The model didn't learn to distinguish palm-up vs palm-down sufficiently
4. **Limited negative diversity:** No real examples of similar-but-different gestures

## Decision

**Abandon Random Forest approach and implement a Feed Forward Neural Network (FFNN).**

### Rationale for FFNN

1. **Better feature learning:** NNs can learn complex non-linear decision boundaries
2. **Embeddings:** Hidden layers can learn to encode subtle differences (palm orientation, wrist position)
3. **Regularization:** Dropout can help prevent overfitting to positive samples
4. **Gradual confidence:** Sigmoid output provides probability rather than hard classification

### Architecture Plan

```
Input Layer: 82 features (63 raw coords + 19 derived features)
    ↓
Hidden Layer 1: 64 neurons, ReLU, Dropout(0.3)
    ↓
Hidden Layer 2: 32 neurons, ReLU, Dropout(0.3)
    ↓
Output Layer: 1 neuron, Sigmoid (probability of Spider-Man gesture)
```

### Required Improvements

1. **Collect REAL negative samples:**
   - Loser sign (palm facing camera)
   - Thumbs up
   - Rock sign
   - Peace sign
   - Open palm
   - Closed fist
   - Random hand positions

2. **Augment training data:**
   - Add noise to coordinates
   - Mirror samples (left/right hand)

3. **Better features for palm orientation:**
   - Cross product of palm vectors
   - Z-depth differences
   - Wrist-to-knuckle angle

## Consequences

### Positive
- Neural network can learn subtle differences between similar gestures
- Better generalization with proper negative samples
- Probability output allows confidence thresholding
- Can fine-tune with additional data without full retraining

### Negative
- Requires more negative sample collection
- Slightly more complex training pipeline
- Need to install PyTorch or TensorFlow
- May need GPU for faster training (optional)

### What We Learned
- Synthetic negatives are not a substitute for real data
- High test accuracy on synthetic data means nothing
- Similar gestures (loser, rock) MUST be in the negative training set
- Palm orientation is the key differentiator that needs strong features

## References
- [ADR-002](002-random-forest-vs-neural-network.md) - Original RF vs NN decision (now revisiting)
- [ADR-006](006-data-collection-strategy.md) - Data collection strategy (needs expansion)
- random_forest_classifier/ - Previous RF implementation
