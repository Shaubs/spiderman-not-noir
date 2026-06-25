# ADR-002: Random Forest vs Neural Network for ML Gesture Detection

**Date:** 2026-06-25  
**Status:** Superseded by [ADR-007](007-random-forest-results-and-ffnn.md)

## Context

If rule-based detection proves insufficient, we need an ML model to classify hand gestures from landmark features. Two approaches were considered:

1. **Random Forest:** Ensemble of decision trees (scikit-learn)
2. **Feedforward Neural Network:** Multi-layer perceptron (PyTorch/TensorFlow)

## Decision

**Use Random Forest as primary ML approach**, with Neural Network as optional alternative.

### Rationale

| Factor | Random Forest | Neural Network |
|--------|---------------|----------------|
| Training data needed | 50-200 samples | 500-5000+ samples |
| Training time | Seconds | Minutes to hours |
| Overfitting risk | Low | High with small datasets |
| Interpretability | Feature importance visible | Black box |
| Hyperparameter tuning | Minimal | Extensive |
| Dependencies | scikit-learn only | PyTorch/TensorFlow (heavy) |
| Hardware | CPU only | GPU recommended |

### Key Considerations

1. **Small Dataset:** We're capturing 50-200 samples. Neural networks overfit with this amount.

2. **Low-Dimensional Input:** Hand landmarks = 21 points × 3 coords = 63 features. Neural networks excel with high-dimensional data (images). For 63 structured features, Random Forest is highly effective.

3. **Structured/Tabular Data:** Landmark coordinates are numerical tabular data where tree-based methods excel.

4. **Quick Iteration:** Train, test, adjust in seconds vs. longer training cycles.

## Consequences

- ✅ Fast training and iteration
- ✅ No GPU required
- ✅ Low overfitting risk
- ✅ Can inspect feature importance for debugging
- ⚠️ May need Neural Network for temporal gesture sequences (LSTM/RNN)
- ⚠️ Neural Network better if scaling to many gesture classes (10+)

## Alternatives Considered

```python
# Neural Network (if needed later)
from sklearn.neural_network import MLPClassifier

nn_model = MLPClassifier(
    hidden_layer_sizes=(64, 32),
    max_iter=500
)
```

## References

- [ML Gesture Guide](../ml_gesture_guide.md)
