# Architecture Decision Records (ADR) Index

This directory contains Architecture Decision Records documenting the evolution of design decisions for the Spider-Man gesture detection project.

## What is an ADR?

An ADR is a document that captures an important architectural decision along with its context and consequences.

## ADR Status

| Status | Meaning |
|--------|---------|
| **Proposed** | Under discussion |
| **Accepted** | Approved and implemented |
| **Deprecated** | No longer valid |
| **Superseded** | Replaced by another ADR |

## Decision Log

| ADR | Title | Date | Status |
|-----|-------|------|--------|
| [001](001-rule-based-vs-ml.md) | Rule-Based vs ML for Gesture Detection | 2026-06-25 | Accepted |
| [002](002-random-forest-vs-neural-network.md) | Random Forest vs Neural Network | 2026-06-25 | Superseded by 007 |
| [003](003-state-machine-for-gesture-sequence.md) | State Machine for Gesture Sequence | 2026-06-25 | Accepted |
| [004](004-upside-down-palm-requirement.md) | Upside-Down Palm Orientation | 2026-06-25 | Accepted |
| [005](005-pose-detection-for-arm-orientation.md) | Pose Detection for Arm Orientation | 2026-06-25 | Accepted |
| [006](006-data-collection-strategy.md) | Data Collection Strategy for ML Training | 2026-06-25 | Accepted |
| [007](007-random-forest-results-and-ffnn.md) | Random Forest Results → Switch to FFNN | 2026-06-25 | Accepted |
| [008](008-ffnn-implementation-results.md) | FFNN Implementation Results (99.4% F1) | 2026-06-25 | Accepted |
| [009](009-simplified-trigger-mechanics.md) | Simplified Trigger Mechanics Based on Real-World Testing | 2026-06-25 | Accepted |
| [010](010-depth-perception-and-collision-mechanics.md) | Depth Perception and Collision Mechanics | 2026-06-26 | Accepted |

## Template for New ADRs

```markdown
# ADR-XXX: Title

**Date:** YYYY-MM-DD  
**Status:** Proposed | Accepted | Deprecated | Superseded

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing and/or doing?

## Consequences
What becomes easier or more difficult because of this change?

## References
- Links to related docs
```

---

**← Back to [Planning Docs](../)**
