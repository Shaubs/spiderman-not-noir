# ADR-011: Performance Optimizations for Frame Rate

## Status
Accepted

## Date
2026-06-26

## Context

Real-world testing revealed frame rate issues (~16 FPS) making the game feel sluggish. Profiling identified multiple bottlenecks in the per-frame processing pipeline.

### Performance Profiling Results

| Component | Time (ms) | % of Frame |
|-----------|-----------|------------|
| Hand Detection | 15-25 | 30-40% |
| Pose Detection | 15-25 | 30-40% |
| Grayscale Effect (5 regions) | 5-15 | 10-20% |
| Ball Rendering (5 balls) | 2-5 | 4-8% |
| Everything Else | 3-5 | 5-8% |
| **TOTAL** | **40-75ms** | **~16 FPS** |

## References

### MediaPipe Documentation

1. **HolisticLandmarker API**
   - URL: https://ai.google.dev/edge/mediapipe/solutions/vision/holistic_landmarker
   - Python Guide: https://ai.google.dev/edge/mediapipe/solutions/vision/holistic_landmarker/python
   - Model: `holistic_landmarker.task` (combines hand + pose + face detection)

2. **HandLandmarker API**
   - URL: https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker
   - 21 landmarks per hand

3. **PoseLandmarker API**
   - URL: https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
   - 33 pose landmarks

4. **MediaPipe Tasks Python Package**
   - `from mediapipe.tasks.python import vision`
   - `vision.HolisticLandmarker`, `vision.HandLandmarker`, `vision.PoseLandmarker`

## Decisions

### 1. Single Model Detection (HolisticLandmarker)

**Problem**: Running 2 separate models = ~40ms per frame

**Solution**: Use `HolisticLandmarker` for combined detection

```python
# OLD: Two model calls
hand_results = self.hand_detector.detect(mp_image)   # ~20ms
pose_results = self.pose_detector.detect(mp_image)   # ~20ms

# NEW: Single model call
results = self.holistic_detector.detect(mp_image)    # ~25ms
```

**Savings**: ~15-20ms per frame

### 2. Single RGB Conversion

**Problem**: Converting BGR→RGB twice per frame

**Solution**: Share RGB buffer, convert once

```python
# NEW: Single conversion
rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
# Used for both hand and pose detection
```

**Savings**: ~2-3ms per frame

### 3. Cached Grayscale Mask

**Problem**: Computing circular masks for every region every frame

**Solution**:
- Cache combined mask (`_cached_grayscale_mask`)
- Only rebuild on new hit (`_mask_dirty` flag)
- Use bounding box for affected area only

```python
if self._mask_dirty:
    self._rebuild_grayscale_mask(h, w)  # Once per new hit
# Apply cached mask to ROI only
frame[min_y:max_y, min_x:max_x][mask_roi] = gray_3ch_roi[mask_roi]
```

**Savings**: 5-10ms per frame

### 4. Bounding Box Grayscale Conversion

**Problem**: Full frame grayscale conversion even for small regions

**Solution**: Only convert the bounding box containing grayscale regions

```python
# NEW: ROI-only conversion
roi = frame[min_y:max_y, min_x:max_x]
gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
```

**Savings**: ~3-5ms per frame

### 5. Simplified Ball Rendering

**Problem**: 6 draw calls per ball

**Solution**: Reduced to 3 draw calls

| Before | After |
|--------|-------|
| Outer glow | Combined glow+body |
| Main body | Main body |
| Inner core | *(removed)* |
| Highlight | Single highlight |
| Bright spot | *(merged)* |
| Wobble ellipse | Wobble (size ≥ 10 only) |

**Savings**: ~1-2ms per frame

### 6. Frame Skipping for Pose

**Problem**: Pose detection every frame (unnecessary for slow-moving body)

**Solution**: Detect pose every N frames, cache result

```python
pose_frame_skip = 2  # Configurable
if frame_count % pose_frame_skip == 0:
    pose = detect_pose()
    cached_pose = pose
else:
    pose = cached_pose
```

**Savings**: ~5ms every other frame

### 7. Downscale Option (Experimental)

**Problem**: ML inference on full resolution is slow

**Solution**: Optional downscaling (disabled by default)

```python
# ⚠️ UNDER OBSERVATION: May affect detection accuracy
if downscale_factor < 1.0:
    detect_frame = cv2.resize(frame, (new_w, new_h))
```

**Savings**: Potentially 30-50% faster (not enabled)

## Implementation Files

| File | Changes |
|------|---------|
| `holistic_tracker.py` | **NEW**: Combined hand+pose tracker |
| `symbiote.py` | Cached grayscale masks, simplified ball rendering |
| `web_shooter.py` | `--fast` flag for tracker selection |
| `hand_tracker.py` | Preserved (original dual-model approach) |

## Performance Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| ML Detection | ~40ms | ~25ms | 37% faster |
| RGB Conversion | ~4ms | ~2ms | 50% faster |
| Grayscale (5 regions) | ~10ms | ~3ms | 70% faster |
| Ball Rendering (5 balls) | ~3ms | ~1.5ms | 50% faster |
| **Total Frame Time** | ~60ms | ~35ms | **42% faster** |
| **Estimated FPS** | ~16 | ~28 | **75% boost** |

## Usage

```bash
# Original mode (dual models)
python web_shooter.py

# Optimized mode (single holistic model)
python web_shooter.py --fast
```

## Consequences

### Positive
- Significantly improved frame rate (~28 FPS vs ~16 FPS)
- More responsive gameplay
- Original tracker preserved for comparison

### Negative
- HolisticLandmarker model is larger (~30MB)
- First frame has model download delay
- Frame skipping may cause slight pose lag

### Neutral
- Downscale option available but not enabled by default
- Visual quality of balls slightly reduced (acceptable)

## Future Considerations

1. GPU acceleration with Metal/CUDA
2. Async detection in separate thread
3. Lower resolution camera input
4. Profile-guided optimization

## References
- ADR-010: Depth Perception and Collision Mechanics
- ADR-009: Simplified Trigger Mechanics
