/**
 * useHandDetection - MediaPipe Hand + Pose detection for browser
 * Detects hand landmarks, gesture, and elbow position
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import {
  HandLandmarker,
  PoseLandmarker,
  FilesetResolver,
  HandLandmarkerResult,
  PoseLandmarkerResult,
} from '@mediapipe/tasks-vision';

// Pose landmark indices
const POSE_LEFT_ELBOW = 13;
const POSE_RIGHT_ELBOW = 14;
// Wrist indices kept for reference (using hand landmarks for wrist position)
// const POSE_LEFT_WRIST = 15;
// const POSE_RIGHT_WRIST = 16;

// Spider-Man gesture detection (thumb, index, pinky extended)
function isSpidermanGesture(landmarks: Array<{ x: number; y: number; z: number }>): boolean {
  if (!landmarks || landmarks.length < 21) return false;

  // Fingertip and MCP (knuckle) indices
  const THUMB_TIP = 4, THUMB_MCP = 2;
  const INDEX_TIP = 8, INDEX_MCP = 5;
  const MIDDLE_TIP = 12, MIDDLE_MCP = 9;
  const RING_TIP = 16, RING_MCP = 13;
  const PINKY_TIP = 20, PINKY_MCP = 17;
  const WRIST = 0;

  // Check if finger is extended (tip is further from wrist than MCP)
  const isExtended = (tipIdx: number, mcpIdx: number): boolean => {
    const tip = landmarks[tipIdx];
    const mcp = landmarks[mcpIdx];
    const wrist = landmarks[WRIST];
    
    const tipDist = Math.hypot(tip.x - wrist.x, tip.y - wrist.y);
    const mcpDist = Math.hypot(mcp.x - wrist.x, mcp.y - wrist.y);
    
    return tipDist > mcpDist * 1.1; // 10% margin
  };

  const isCurled = (tipIdx: number, mcpIdx: number): boolean => !isExtended(tipIdx, mcpIdx);

  // Spider-Man: Thumb + Index + Pinky extended, Middle + Ring curled
  const thumbOut = isExtended(THUMB_TIP, THUMB_MCP);
  const indexOut = isExtended(INDEX_TIP, INDEX_MCP);
  const middleCurled = isCurled(MIDDLE_TIP, MIDDLE_MCP);
  const ringCurled = isCurled(RING_TIP, RING_MCP);
  const pinkyOut = isExtended(PINKY_TIP, PINKY_MCP);

  return thumbOut && indexOut && middleCurled && ringCurled && pinkyOut;
}

export interface HandDetectionResult {
  landmarks: Array<{ x: number; y: number; z: number }> | null;
  handedness: 'Left' | 'Right' | null;
  isSpiderman: boolean;
  wristPos: { x: number; y: number } | null;
  elbowPos: { x: number; y: number } | null;
}

export function useHandDetection(
  videoRef: React.RefObject<HTMLVideoElement>,
  enabled: boolean = true
) {
  const handLandmarkerRef = useRef<HandLandmarker | null>(null);
  const poseLandmarkerRef = useRef<PoseLandmarker | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastResultRef = useRef<HandDetectionResult>({
    landmarks: null,
    handedness: null,
    isSpiderman: false,
    wristPos: null,
    elbowPos: null,
  });

  // Initialize both landmarkers
  useEffect(() => {
    if (!enabled) return;

    let mounted = true;

    const initLandmarkers = async () => {
      try {
        console.log('Initializing MediaPipe landmarkers...');
        
        const vision = await FilesetResolver.forVisionTasks(
          'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
        );

        // Initialize Hand Landmarker
        const handLandmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath:
              'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
            delegate: 'GPU',
          },
          runningMode: 'VIDEO',
          numHands: 1,
          minHandDetectionConfidence: 0.5,
          minHandPresenceConfidence: 0.5,
          minTrackingConfidence: 0.5,
        });

        // Initialize Pose Landmarker
        const poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath:
              'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
            delegate: 'GPU',
          },
          runningMode: 'VIDEO',
          numPoses: 1,
          minPoseDetectionConfidence: 0.5,
          minPosePresenceConfidence: 0.5,
          minTrackingConfidence: 0.5,
        });

        if (mounted) {
          handLandmarkerRef.current = handLandmarker;
          poseLandmarkerRef.current = poseLandmarker;
          setIsReady(true);
          console.log('Hand + Pose landmarkers initialized');
        }
      } catch (err) {
        console.error('Failed to initialize landmarkers:', err);
        if (mounted) {
          setError(`Landmarker init failed: ${err}`);
        }
      }
    };

    initLandmarkers();

    return () => {
      mounted = false;
      handLandmarkerRef.current?.close();
      poseLandmarkerRef.current?.close();
      handLandmarkerRef.current = null;
      poseLandmarkerRef.current = null;
    };
  }, [enabled]);

  // Detect hands and pose in current video frame
  const detect = useCallback((): HandDetectionResult => {
    const video = videoRef.current;
    const handLandmarker = handLandmarkerRef.current;
    const poseLandmarker = poseLandmarkerRef.current;

    if (!video || !handLandmarker || !poseLandmarker || !isReady || video.readyState < 2) {
      return lastResultRef.current;
    }

    try {
      const timestamp = performance.now();
      
      // Run hand detection
      const handResult: HandLandmarkerResult = handLandmarker.detectForVideo(video, timestamp);
      
      // Run pose detection
      const poseResult: PoseLandmarkerResult = poseLandmarker.detectForVideo(video, timestamp);

      let landmarks: Array<{ x: number; y: number; z: number }> | null = null;
      let handedness: 'Left' | 'Right' | null = null;
      let isSpiderman = false;
      let wristPos: { x: number; y: number } | null = null;
      let elbowPos: { x: number; y: number } | null = null;

      // Extract hand data
      if (handResult.landmarks && handResult.landmarks.length > 0) {
        landmarks = handResult.landmarks[0];
        handedness = handResult.handednesses?.[0]?.[0]?.categoryName as 'Left' | 'Right' || 'Right';
        isSpiderman = isSpidermanGesture(landmarks);
        const wrist = landmarks[0];
        if (wrist) {
          wristPos = { x: wrist.x, y: wrist.y };
        }
      }

      // Extract elbow from pose based on which hand is detected
      if (poseResult.landmarks && poseResult.landmarks.length > 0) {
        const pose = poseResult.landmarks[0];
        
        // Determine which elbow to use based on handedness
        // Note: In mirrored view, left/right are swapped
        if (handedness === 'Left') {
          // Use right elbow (appears on left side of mirrored view)
          const elbow = pose[POSE_RIGHT_ELBOW];
          if (elbow) {
            elbowPos = { x: elbow.x, y: elbow.y };
          }
        } else {
          // Use left elbow (appears on right side of mirrored view)
          const elbow = pose[POSE_LEFT_ELBOW];
          if (elbow) {
            elbowPos = { x: elbow.x, y: elbow.y };
          }
        }
        
        // Fallback: if no hand detected, try to find elbow near detected wrist in pose
        if (!elbowPos && !handedness) {
          // Check both elbows and pick whichever has better visibility
          const leftElbow = pose[POSE_LEFT_ELBOW];
          const rightElbow = pose[POSE_RIGHT_ELBOW];
          
          if (leftElbow && leftElbow.visibility && leftElbow.visibility > 0.5) {
            elbowPos = { x: leftElbow.x, y: leftElbow.y };
          } else if (rightElbow && rightElbow.visibility && rightElbow.visibility > 0.5) {
            elbowPos = { x: rightElbow.x, y: rightElbow.y };
          }
        }
      }

      lastResultRef.current = {
        landmarks,
        handedness,
        isSpiderman,
        wristPos,
        elbowPos,
      };
    } catch (err) {
      // Silently handle detection errors (common during startup)
    }

    return lastResultRef.current;
  }, [videoRef, isReady]);

  return { detect, isReady, error };
}
