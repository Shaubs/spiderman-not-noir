# Potential Issues & Known Limitations

This document tracks known issues, potential problems, and areas requiring attention in the Spider-Man Web Shooter project.

---

## 🔴 High Priority Issues

### 1. Trigger Logic May Be Too Sensitive

**Status**: Under Observation  
**ADR Reference**: ADR-009

**Description**:
The current trigger mechanics may fire unintentionally:

| Trigger | Setting | Potential Issue |
|---------|---------|-----------------|
| RAPID_TOGGLE | 2 toggles in 0.5s | Can fire accidentally with shaky hand detection |
| SUSTAINED_HOLD | 0.4 seconds | Very short - may fire when user is just holding pose |
| ARMED_MOTION | 4% upward movement | Small hand movements can trigger |

**Symptoms**:
- Webs firing when user doesn't intend to shoot
- Multiple rapid fires in succession
- Trigger fires immediately when pose is detected

**Potential Solutions**:
1. Increase `sustained_hold_seconds` to 0.6-0.8s
2. Increase `toggle_count_threshold` to 3
3. Add debounce/hysteresis to detection

---

### 2. HolisticLandmarker Model Download on First Run

**Status**: Known Behavior  
**ADR Reference**: ADR-011

**Description**:
The holistic model (~30MB) downloads on first run, causing startup delay.

**Symptoms**:
- 5-10 second delay on first `--fast` run
- Appears to hang before camera opens

**Potential Solutions**:
1. Pre-download model in setup script
2. Add progress indicator during download
3. Include model in Docker image

---

### 3. Frame Skip May Cause Pose Lag

**Status**: Under Observation  
**ADR Reference**: ADR-011

**Description**:
Pose detection runs every 2 frames (`pose_frame_skip=2`), which may cause:
- Elbow position to be stale for 1 frame
- Web direction slightly off during fast movement

**Symptoms**:
- Web shoots in slightly wrong direction during rapid arm movement
- Pose landmarks visually lag behind actual position

**Potential Solutions**:
1. Reduce `pose_frame_skip` to 1 (full detection every frame)
2. Interpolate pose between frames
3. Accept as tradeoff for performance

---

## 🟡 Medium Priority Issues

### 4. Grayscale Effect Accumulates Without Limit

**Status**: Design Decision  
**ADR Reference**: ADR-010

**Description**:
Grayscale regions are permanent and accumulate. With many hits, the entire screen can become grayscale.

**Symptoms**:
- Screen becomes progressively more gray
- No visual feedback on how "damaged" player is
- No game-over condition when fully gray

**Potential Solutions**:
1. Add game-over when X% of screen is grayscale
2. Implement health bar based on grayscale coverage
3. Allow grayscale to fade after extended time

---

### 5. Symbiote Targeting Removed

**Status**: Design Change  
**ADR Reference**: N/A (this session)

**Description**:
Changed from body-part targeting to random screen positions. This may make the game feel less personal/threatening.

**Impact**:
- Symbiotes no longer "hunt" the player
- Less immersive "attack" feel
- May be too easy if player stands still

**Potential Solutions**:
1. Hybrid approach: 50% random, 50% body-targeted
2. Add difficulty mode that re-enables targeting
3. Keep random but bias toward detected person region

---

### 6. Camera Access in Docker

**Status**: Not Tested  
**ADR Reference**: ADR-011 (Docker plan)

**Description**:
Docker containers have limited camera access, especially on macOS.

**Potential Issues**:
- `--privileged` mode required on Linux
- macOS needs XQuartz + special setup
- Windows needs different approach

**Potential Solutions**:
1. Use native Python installation for game
2. Docker only for training/CI
3. Document platform-specific workarounds

---

## 🟢 Low Priority / Minor Issues

### 7. MediaPipe Warning Messages

**Status**: Cosmetic  

**Description**:
MediaPipe outputs warning about `NORM_RECT without IMAGE_DIMENSIONS`:
```
W0000 00:00:... landmark_projection_calculator.cc:81] Using NORM_RECT without IMAGE_DIMENSIONS...
```

**Impact**: None - just console noise

**Potential Solutions**:
1. Suppress MediaPipe logging
2. Configure IMAGE_DIMENSIONS if possible
3. Ignore (harmless warning)

---

### 8. Ball Rendering Simplified

**Status**: Tradeoff Accepted  
**ADR Reference**: ADR-011

**Description**:
Ball rendering reduced from 6 to 3 draw calls for performance. Visual quality slightly reduced.

**Impact**:
- Balls look slightly less "jelly-like"
- Inner core removed
- Wobble only on larger balls (≥10px)

**Potential Solutions**:
1. Add quality toggle (performance vs. visual)
2. Use sprite/texture instead of primitives
3. Accept tradeoff

---

## 📋 Tracking

| Issue | Priority | Status | Owner | Target |
|-------|----------|--------|-------|--------|
| Trigger sensitivity | High | Observing | - | TBD |
| Model download delay | High | Known | - | Setup script |
| Pose frame skip lag | Medium | Observing | - | TBD |
| Grayscale accumulation | Medium | Design | - | Game-over logic |
| Random targeting | Medium | Design | - | Feedback needed |
| Docker camera | Medium | Not tested | - | TBD |
| MediaPipe warnings | Low | Cosmetic | - | Ignore |
| Ball visuals | Low | Accepted | - | N/A |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-26 | Initial document created |
| 2026-06-26 | Added trigger sensitivity analysis |
| 2026-06-26 | Added performance optimization tradeoffs |
| 2026-06-26 | Added symbiote targeting change note |
