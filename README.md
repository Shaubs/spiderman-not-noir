# 🕷️ Spider-Man: Not Noir

A real-time computer vision game where you shoot symbiote balls with web gestures before they turn the world grayscale (noir). Uses hand tracking, gesture recognition, and neural networks to detect the iconic Spider-Man web-shooting pose.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-green.svg)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)

## 🎮 Gameplay

- **Objective**: Survive as long as possible by shooting symbiote balls before they hit you
- **Gesture**: Make the Spider-Man hand pose (thumb + index + pinky extended, middle + ring folded)
- **Trigger**: Flick your hand, move UP, or hold the gesture to shoot webs
- **Dr. Strange Mode**: Catch the portal ring to unlock magic powers - draw a closed loop to restore reality!

### Controls
| Key | Action |
|-----|--------|
| `SPACE` | Start game / Restart |
| `Q` | Quit |
| `S` | Screenshot |
| `R` | Reset state machine |
| `G` | Reset game |

## 🛠️ Tech Stack

### Core Technologies
- **Python 3.10+** - Primary language
- **OpenCV 4.8+** - Real-time video capture and rendering
- **MediaPipe** - Hand and pose landmark detection
- **PyTorch** - Neural network for gesture classification

### ML Models
- **Hand Landmarker** - 21-point hand skeleton detection
- **Pose Landmarker** - Full body pose for arm orientation
- **FFNN Classifier** - Feed-forward neural network for Spider-Man gesture recognition
- **Multi-Gesture Classifier** - Extended classifier for Dr. Strange gesture detection

## 📁 Project Structure

```
spiderman-not-noir/
├── game.py                    # 🎮 Main game entry point
├── main.py                    # Alternative entry point
├── requirements.txt           # Python dependencies
│
├── tracking/                  # 🎯 Hand/Pose Tracking & Gesture Detection
│   ├── hand_tracker.py        # Dual-model hand + pose tracker
│   ├── holistic_tracker.py    # Single-model optimized tracker
│   ├── gesture_detector.py    # Gesture detection base classes
│   └── gesture_state_machine.py # Temporal state tracking for triggers
│
├── rendering/                 # 🎨 Graphics & Visual Effects
│   ├── graphics_manager.py    # THWIP effects, hand styling
│   └── web_renderer.py        # Web shooting visual effects
│
├── game_mechanics/            # 🎲 Game Logic
│   ├── enemies/               # Symbiote balls, infection system
│   │   ├── symbiote.py        # Flying symbiote ball entities
│   │   └── infection.py       # BFS infection spread effect
│   ├── dr_strange/            # Portal rings, warp effects
│   │   ├── ring.py            # Dr. Strange portal ring system
│   │   └── warp_portal.py     # Swirling warp visual effect
│   └── screens/               # Game screens, HUD
│       ├── game_screen.py     # Intro, HUD, game over screens
│       └── training_mode.py   # Practice mode
│
├── classifiers/               # 🧠 ML Gesture Classifiers
│   ├── ffnn/                  # Feed-forward neural network
│   │   ├── model.pt           # Trained model weights
│   │   ├── train.py           # Training script
│   │   └── run_classifier.py  # Real-time classification
│   └── random_forest/         # Legacy random forest classifier
│
├── config/                    # ⚙️ Configuration
│   ├── colors.py              # Color constants (FIRE_COLORS, etc.)
│   ├── dimensions.py          # Frame dimensions
│   ├── game.py                # Game configuration
│   ├── symbiote.py            # Symbiote ball settings
│   ├── score.py               # Scoring configuration
│   └── depth.py               # Depth/Z-axis configuration
│
├── entities/                  # 🏗️ Base Entity Classes
│   └── base.py                # FlyingEntity, EntityManager
│
├── models/                    # 📦 MediaPipe Model Files
│   ├── hand_landmarker.task   # Hand detection model
│   ├── holistic_landmarker.task # Combined hand+pose model
│   └── pose_landmarker.task   # Pose detection model
│
├── apps/                      # 📱 Application Variants
│   ├── web_shooter.py         # Landmarks mode (shows skeleton)
│   ├── web_shooter_glove.py   # Glove mode (filled hand)
│   └── web_shooter_base.py    # Shared base class
│
├── gestures/                  # ✋ Gesture Definitions
│   └── spiderman.py           # Spider-Man gesture rules
│
├── multi_gesture_classifier/  # 🔮 Multi-Gesture Detection
│   ├── train.py               # Training for multiple gestures
│   └── run_classifier.py      # Real-time multi-gesture detection
│
├── ffnn_training_samples/     # 📊 Training Data
│   ├── spiderman/             # Positive samples
│   ├── closed_fist/           # Negative samples
│   ├── open_palm/             # Negative samples
│   ├── thumbs_up/             # Negative samples
│   ├── dr_strange/            # Dr. Strange samples
│   └── random/                # Random hand poses
│
├── data_creation_lab/         # 🧪 Data Collection Tools
│   ├── collect_samples.py     # Sample collection script
│   └── collect_negatives.py   # Auto-sequencing multi-gesture collection
│
├── planning_docs/             # 📝 Architecture Decision Records
│   └── decisions/             # ADRs (see below)
│
├── assets/                    # 🎨 Game Assets
│   └── thwip.png              # THWIP! overlay image
│
└── snapshots/                 # 📸 Screenshots
```

## 📝 Planning Documents (ADRs)

The `planning_docs/decisions/` folder contains Architecture Decision Records documenting key design choices:

| ADR | Title | Summary |
|-----|-------|---------|
| 001 | Rule-Based vs ML | Chose ML for gesture detection |
| 002 | Random Forest vs Neural Network | Compared classifiers |
| 003 | State Machine for Gesture Sequence | Temporal detection design |
| 004 | Upside-Down Palm Requirement | Palm orientation rules |
| 005 | Pose Detection for Arm Orientation | Using pose for web direction |
| 006 | Data Collection Strategy | Training data approach |
| 007 | Random Forest Results | Initial classifier results |
| 008 | FFNN Implementation | Neural network implementation |
| 009 | Simplified Trigger Mechanics | Flick/hold/upward triggers |
| 010 | Depth Perception & Collision | 3D depth simulation |
| 011 | Performance Optimizations | Frame rate improvements |
| 012 | Graphics & Refactoring | Visual effects system |
| 013-016 | Streaming/Tauri POCs | Web streaming experiments |
| 017 | PyInstaller Distribution | Desktop app packaging |
| 018 | Dr. Strange Gesture | Magic portal system |

## 🚀 Installation

### Prerequisites
- Python 3.10 or higher
- Webcam
- macOS / Windows / Linux

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/spiderman-not-noir.git
   cd spiderman-not-noir
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the game**
   ```bash
   python game.py
   ```

### First Run Notes
- MediaPipe models will be downloaded automatically on first run
- Position yourself so your upper body is visible in the webcam
- Good lighting helps with hand detection accuracy

## 🎯 How to Play

1. **Start the game** - Press `SPACE` on the intro screen
2. **Make the Spider-Man pose** - Extend thumb, index, and pinky; fold middle and ring fingers
3. **Shoot webs** - Any of these triggers work:
   - **Flick**: Quickly toggle the gesture on/off
   - **Move UP**: Hold gesture and move hand upward
   - **Hold**: Maintain gesture for 0.5 seconds
4. **Destroy symbiotes** - Hit the black balls before they reach you
5. **Avoid hits** - Each hit spreads grayscale infection on screen
6. **Dr. Strange Mode** - Catch the orange portal ring to unlock magic powers!

## 🔧 Alternative Entry Points

```bash
# Main game (glove mode - filled red hand)
python game.py

# Web shooter with hand skeleton visible
python -m apps.web_shooter

# Web shooter with glove mode
python -m apps.web_shooter_glove

# Fast mode (single model, better performance)
python -m apps.web_shooter --fast
```

## 🏗️ Building Standalone App

```bash
# Build macOS app
./build.sh

# Or manually with PyInstaller
pyinstaller SpiderMan-Not-Noir.spec
```

The built app will be in `dist/SpiderMan-Not-Noir.app`

## 📊 Training Your Own Model

1. **Collect training data**
   ```bash
   python data_creation_lab/collect_negatives.py
   ```

2. **Train the FFNN classifier**
   ```bash
   python classifiers/ffnn/train.py
   ```

3. **Test the classifier**
   ```bash
   python classifiers/ffnn/run_classifier.py
   ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Read the ADRs in `planning_docs/decisions/` for context
4. Make your changes
5. Run the game to test (`python game.py`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is for educational purposes. Spider-Man is a trademark of Marvel Entertainment.

---

*"With great power comes great responsibility." - Uncle Ben*
