# Articulated companion animation contract (v1)

## Required files per companion
- `model.json`: skeleton names and local transforms, z-order, bounds, anchors and material references.
- `rig/`: isolated RGBA components with registration coordinates, not cropped arbitrary patches.
- `expressions.json`: blendshape/eye/mouth morph targets or frame sets.
- `motion/*.json`: authored motion curves and state transitions.
- `audio/`: optional approved voice samples. Text-to-speech is opt-in.

## Mandatory control API
`setEmotion(emotion, intensity)`, `moveTo(x,y)`, `lookAt(x,y)`, `speak(audio,visemes)`, `setActivity(activity)`, `cancelActivity()`, `onStatusChange(taskEvent)`.

## Emotion taxonomy
`neutral, happy, excited, proud, curious, wonder, thinking, processing, concentrating, working, speaking, annoyed, angry, disappointed, sad, hurt, pain, alarmed, panic, bored, sleepy, sleeping, relieved, celebrating`.

## Articulation acceptance
Independent bilateral eyes, blink, brows, cheeks, lips, head, torso, 2 arms/elbows/wrists/hands, 2 legs/knees/feet; walk cycles with planted feet and natural gait; nonrigid hair/ribbon response; turn and sit/stand transitions; facial lip sync; physically consistent clothing layers; no crossfade from a full-body still as a substitute for rigging.

Use Rive or Live2D-style rigging for detailed 2D assets, or Blender/VRM-based 3D rigs where superior. Commercial licensing, runtime compatibility, and performance must be verified before adoption.


## A1.1 engineering delivery

`orchestrator/frontend/puppet_engine.mjs` provides per-joint world transforms, blended pose states, two-bone IK for hand reach, input-responsive gaze, blink cycles, independent mouth viseme sprite overlays, and secondary hair physics. `/puppet-lab` is the test tool, not production-quality character artwork. For each character create actual transparent independently painted parts for all `REQUIRED_LAYERS` (20 minimum), extra closed eye layers and viseme PNGs. Preserve concealed seam overlap at every limb connection. Inspect elbow/shoulder skin deformation, finger-to-forearm connection, planted feet during walking and extreme expressions at several sizes. Owner approval is mandatory before marking a character rig production-ready.
