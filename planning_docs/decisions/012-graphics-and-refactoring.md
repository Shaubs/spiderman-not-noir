# ADR-012: Graphics Improvements and Code Refactoring

**Date:** 2026-06-26  
**Status:** Implemented  
**Context:** Post-optimization phase (ADR-011), improving visual feedback and code maintainability

## Decision

### 1. Graphics Improvements

#### Hand Rendering - Glove Mode
- **Filled red palm polygon** (landmarks 1, 5, 9, 13, 17, 0)
- **Thick red connectors** (20px) for glove appearance
- **No landmark dots** - cleaner visual
- **No pose/face landmarks** in glove mode

#### Hand Rendering - Landmarks Mode
- Spider-Man styled landmarks (red connections, blue dots)
- Optional landmark numbers display
- Optional pose landmark overlay

#### THWIP Effect
- PNG overlay at **collision position** (not web origin)
- Pre-scaled sizes for performance
- Fade-out animation

#### Web Rendering
- Simple line-based rendering (reverted from particle trail)
- 3-line spread with glow effect
- Faster than particle system (~1ms vs ~2ms)

### 2. Code Refactoring

Extracted common code to shared modules:

#### New Files
- `web_renderer.py` - WebLine, WebShot, WebEffectRenderer classes
- `web_shooter_base.py` - BaseWebShooter abstract class

#### Simplified App Files
| File | Lines Before | Lines After | Reduction |
|------|-------------|-------------|-----------|
| web_shooter.py | 575 | 68 | 88% |
| web_shooter_glove.py | 481 | 55 | 89% |

#### BaseWebShooter Abstract Methods
Subclasses only need to implement:
- `draw_hand()` - hand rendering style
- `draw_pose_if_enabled()` - pose visibility
- `get_controls_text()` - UI hints
- `get_window_title()` - window title
- `handle_extra_keys()` - mode-specific controls

## Consequences

### Positive
- **~87% code reduction** in main app files
- **Single source of truth** for game logic
- **Easy to add new modes** (just extend BaseWebShooter)
- **Faster web rendering** (lines vs particles)
- **THWIP appears at hit location** - better visual feedback

### Negative
- Additional import dependencies
- Slightly more complex file structure

## Files Modified
- `graphics_manager.py` - draw_spiderman_hand_filled updated
- `web_renderer.py` - NEW shared web rendering
- `web_shooter_base.py` - NEW base class
- `web_shooter.py` - Refactored to use base
- `web_shooter_glove.py` - Refactored to use base

## Performance Impact
- Web rendering: ~2ms → ~1ms (50% faster)
- No impact on gesture detection (rendering is post-detection)
