# ADR-010: Depth Perception and Collision Mechanics

## Status
Accepted

## Date
2026-06-26

## Context

After implementing the basic web shooter game with symbiote balls, real-world testing revealed that the depth perception and collision mechanics needed significant improvement for a more immersive and intuitive gameplay experience.

### Observations from Testing

1. **Ball Depth Perception**: Balls starting at 15px didn't convey a strong sense of distance. Starting at 1px creates a more dramatic "approaching from far away" effect.

2. **Hit Feedback**: When balls hit the player, there was no visual impact on the player's body. Converting the hit area to grayscale creates a "symbiote infection" visual effect.

3. **Web Coverage**: A single web line was too narrow and didn't convey the 3D spreading nature of actual spider webs.

4. **Collision Detection**: Needed clearer definition of how web-ball collisions work with the new 3-line web system.

5. **Z-Coordinate System**: The implicit depth system (using size as proxy) needed explicit configuration for better maintainability.

6. **Ball Motion**: Perfectly straight trajectories felt mechanical; organic wobble motion would feel more alive.

## Decisions

### 1. Ball Spawn Size: 1 Pixel

**Decision**: Balls spawn at 1 pixel and grow to 80 pixels as they approach.

**Rationale**:
- Creates stronger depth perception
- Balls appear as tiny dots in the distance, growing dramatically
- More visually impressive and game-like

**Formula**:
```
size = 1 + (end_size - 1) * progress
where progress = elapsed_time / travel_time (0.0 to 1.0)
```

### 2. Grayscale Hit Effect

**Decision**: When a ball hits the player, a circular region around the hit location converts from RGB to grayscale **permanently** until game reset.

**Rationale**:
- Creates visual feedback of "symbiote infection"
- Thematic with Spider-Man/Venom lore (symbiote spreads and stays)
- Clear indication of accumulated damage
- Permanent effect adds stakes to gameplay

**Implementation**:
- Circular mask at hit location
- Radius = 1.5 × ball's final size
- Grayscale conversion: `cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)`
- **No fade** - regions persist until game reset (`g` key)
- Multiple hits accumulate grayscale regions

### 3. Three-Line Web Spread

**Decision**: Web shoots as 3 lines - center line plus two lines at ±15° angles.

**Rationale**:
- Creates a "cone" effect mimicking real web spreading
- Better coverage for hitting balls
- Conveys depth perception (lines spread further apart at distance)

**Geometry**:
```
At distance D from wrist:
  spread_width = 2 × D × tan(15°) ≈ 0.536 × D

Example coverage:
  100px away: 53.6px wide
  300px away: 160.8px wide  
  500px away: 268px wide
```

### 4. Collision Detection: Line-Circle Intersection

**Decision**: Collision occurs if any of the 3 web lines intersects with the ball's circular area.

**Algorithm**:
```
For each line (left, center, right):
  1. Find closest point on line segment to ball center
  2. Calculate distance from closest point to ball center
  3. If distance ≤ ball_radius → COLLISION

Closest Point Formula:
  t = clamp(dot(AP, AB) / dot(AB, AB), 0, 1)
  closest = A + t × AB
  distance = length(ball_center - closest)
```

**Rationale**: 
- Simple and fast (2D check, instant)
- No depth timing complexity for now
- 3 lines provide good coverage

### 5. Explicit Z-Coordinate Configuration

**Decision**: Create `depth_config/` folder with explicit Z-axis configuration.

**Structure**:
```
depth_config/
    __init__.py
    z_config.py
```

**Z-Coordinate System**:
- `z = 1.0`: Far away (spawn point)
- `z = 0.0`: At player (screen plane)
- Relationship: `z = 1.0 - progress`

**Configuration Fields**:
- `z_far`: 1.0 (spawn depth)
- `z_near`: 0.0 (player depth)
- `size_at_far`: 1 pixel
- `size_at_near`: 80 pixels
- `travel_time`: 3.0 seconds

### 6. Ball Wobble Motion

**Decision**: Balls wobble perpendicular to their travel direction using sinusoidal motion, with amplitude decreasing as they approach.

**Formula**:
```
perpendicular = rotate_90_degrees(travel_direction)
amplitude = max_amplitude × (1.0 - progress)
wobble_offset = sin(time × frequency × 2π + phase) × amplitude
final_position = linear_position + perpendicular × wobble_offset
```

**Parameters**:
- `wobble_amplitude`: 20 pixels (max)
- `wobble_frequency`: 3 Hz
- Amplitude decreases to 0 as ball approaches (focused targeting)

**Rationale**:
- Balls feel organic and "alive" (jelly-like)
- More challenging to track
- Amplitude reduction ensures balls still hit their target

### 7. Web Direction: Elbow to Wrist

**Decision**: Web line originates from elbow and extends through the wrist outward.

**Implementation**: 
- Start point: Pose landmark (elbow) - left_elbow (13) or right_elbow (14)
- Direction: Through hand landmark 0 (wrist), extending to frame edge
- Handedness detection: Uses MediaPipe handedness to pick correct elbow

**Rationale**: 
- Creates a more natural "arm shooting" visual
- Web appears to travel along the forearm direction
- Better matches Spider-Man's web-slinging posture

**Coordinates**:
```
elbow = pose_landmarks[13 or 14]  # Based on handedness
wrist = hand_landmarks[0]
direction = normalize(wrist - elbow)
web_end = elbow + direction × max_distance
```

### 8. Web-Ball Collision Feedback

**Decision**: Print "THWACK!" only when web successfully destroys a ball (not on every trigger).

**Rationale**:
- Clear audio/visual feedback tied to actual hits
- Silent web shots until contact made
- More satisfying hit confirmation

## Consequences

### Positive
- **Better Depth Perception**: 1px spawn + size growth creates dramatic approaching effect
- **Clear Hit Feedback**: Grayscale effect shows exactly where player was hit
- **Wider Web Coverage**: 3-line spread improves hit rate and looks more realistic
- **Maintainable Code**: Explicit Z-config separates depth logic from game logic
- **Organic Feel**: Wobble motion makes balls feel alive

### Negative
- **Performance**: 3 lines = 3× collision checks per web (acceptable overhead)
- **Complexity**: More configuration parameters to tune
- **Grayscale Processing**: Per-frame pixel manipulation has minor cost

### Neutral
- **Instant Collision**: Keeping depth-based collision timing for future consideration
- **Web Travel Time**: May add web Z-travel in future iteration

## Implementation Files

| File | Changes |
|------|---------|
| `depth_config/__init__.py` | New: Package init |
| `depth_config/z_config.py` | New: Z-axis configuration |
| `symbiote_config.py` | New: `start_size = 1`, grayscale params |
| `symbiote.py` | New: Wobble motion, permanent grayscale, depth config |
| `web_shooter.py` | Update: 3-line web, elbow-to-wrist direction, THWACK on collision |
| `hand_tracker.py` | Update: Full body pose tracking (elbows for web direction) |

## Future Considerations

1. **Gravity Arc**: Web trajectory with slight downward curve
2. **Depth-Based Collision**: Web travel time matching ball Z-position
3. **Web Catch-Up**: Web must intercept ball at matching depth
4. **Game Over State**: When grayscale covers significant portion of screen

## References
- ADR-009: Simplified Trigger Mechanics
- ADR-008: FFNN Implementation Results
