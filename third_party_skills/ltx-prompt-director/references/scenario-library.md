# Scenario Library

Use these as routing recipes. Replace placeholders and adapt duration, aspect ratio, references and audio. Do not copy every adjective blindly.

## 1. Cinematic establishing shot

**Route:** T2V.  
**Prompt focus:** geography, atmosphere, one environmental action, slow camera.  
**Pattern:** wide establishing shot → foreground movement → camera reveal → ambience → stable end.

## 2. Character entrance

**Route:** T2V or I2V; FLF when end mark matters.  
**Pattern:** empty/held opening → subject enters from a named direction → wardrobe secondary motion → camera reframes → footsteps/door Foley → final mark.

## 3. Emotional close-up

**Route:** I2V preferred for identity.  
**Pattern:** blink/breath → gaze shift → small facial cue → slow push-in → sparse ambience.  
Avoid dramatic full-face deformation.

## 4. Fashion lookbook

**Route:** I2V + identity reference; Prompt Relay for several poses.  
**Pattern:** stable full body → quarter turn → fabric reaction → one step → final pose.  
Use clean studio sound or music; lock face and garment.

## 5. Beauty commercial

**Route:** I2V/T2V + product/face reference.  
Use macro skin/product details, slow light sweep, controlled turn, no exact text. Reserve negative space for post copy.

## 6. Product hero reveal

**Route:** T2V/I2V + Prompt Relay.  
Beats: static hero → light sweep → mechanical reveal → orbit → final hold. Add precise Foley and a restrained music sting.

## 7. Unboxing

**Route:** I2V or T2V; hand quality may require controlled framing/retakes.  
Beats: hands approach → seal breaks → lid opens → product lift → reaction. Keep one hand action per beat.

## 8. Food macro

**Route:** T2V/I2V.  
Describe viscosity, steam, crumbs, cut/pour motion, macro lens feel and Foley. Avoid combining several impossible food transformations.

## 9. Architectural walkthrough

**Route:** T2V with camera control/depth reference where precision matters.  
Prompt material, light and parallax; let depth/camera control own geometry. Use continuous footsteps/room tone.

## 10. Automotive commercial

**Route:** T2V/I2V + camera/motion control.  
One driving maneuver per shot. Lock vehicle design with references. Use tire/engine/wind audio and believable reflections.

## 11. Drone/aerial landscape

**Route:** T2V.  
Specify altitude, path, reveal direction, weather, water/foliage motion and ambience. Avoid changing geography mid-shot.

## 12. Dance performance

**Route:** A2V/custom audio + pose/motion control.  
Audio owns tempo, pose signal owns body, prompt owns character, wardrobe, environment, camera and secondary motion.

## 13. Fight/action beat

**Route:** pose/motion reference or Prompt Relay.  
Break into anticipation → one attack → impact → recovery. Do not request a long choreography with multiple unanchored fighters in one short shot.

## 14. Sports shot

**Route:** I2V/T2V + motion/pose control.  
Name ball/object trajectory, player action, camera follow, crowd/impact sound and ending. Use slow motion only around a defined moment.

## 15. Horror reveal

**Route:** T2V/I2V + Relay.  
Establish stillness → subtle off-screen cue → controlled reveal → physical reaction → silence/impact. Avoid generic “scary” without visible cause.

## 16. Sci-fi transformation

**Route:** Prompt Relay + FLF/FML if endpoints matter.  
Use staged material changes; preserve anatomy/identity; specify where transformation begins and how it propagates.

## 17. Fantasy magic effect

**Route:** T2V/I2V + effect LoRA optional.  
Tie particles/light to hand or object motion. Limit effect channels; avoid covering the face.

## 18. Anime scene

**Route:** T2V/I2V + style LoRA optional.  
Specify cel shading, linework, limited/smooth animation style, controlled smears, background parallax and voice style. Avoid mixing photoreal skin terms.

## 19. Stop-motion miniature

**Route:** T2V.  
Describe tangible materials, incremental motion, miniature depth of field, handcrafted imperfections and small practical sounds.

## 20. Documentary interview

**Route:** I2V/A2V/talking avatar.  
Stable framing, natural articulation, subtle gestures, room tone, no dramatic camera. Use supplied audio for exact speech.

## 21. News presenter/social explainer

**Route:** talking avatar + TTS/reference audio.  
Portrait aspect if needed, direct eye contact, restrained gestures, clean background, stable camera. Add graphics/text later.

## 22. Podcast conversation

**Route:** separate speaker close-ups + master two-shot; multi-character workflow only when needed.  
Use clean TTS/reference stems, listener reaction shots, consistent spatial labels and edit in post.

## 23. Two-person dramatic dialogue

**Route:** Prompt Relay + custom audio or native dialogue.  
Global two-shot; A line; reaction; B line; final silence. One speaker per segment.

## 24. Group conversation

**Route:** shot/reverse-shot production rather than one overloaded generation.  
Use a master establishing shot, then individual close-ups. Maintain a continuity ledger for wardrobe, seating and lighting.

## 25. Multilingual dubbing

**Route:** Lipdub.  
Preserve source performance, replace speech with supplied translated audio, adjust translation duration beforehand, preserve ambience.

## 26. Add voice to silent video

**Route:** Just-Talk/masked V2V or lip-sync workflow.  
Preserve source clip; target only face/mouth; supply exact audio; prompt natural articulation and no other changes.

## 27. Foley generation

**Route:** V2V Foley/audio workflow.  
List visible events in order and add one environmental bed. No dialogue/music unless requested.

## 28. Music video

**Route:** custom audio + Prompt Relay/movie-maker.  
Use waveform/lyric timestamps, one readable visual action per major phrase, planned camera/light evolution, segment export for editing.

## 29. Audio-reactive abstract visual

**Route:** A2V/audio-reactive LoRA.  
Map bass to one property and treble/vocals to another. Keep camera stable enough to perceive the reaction.

## 30. First-to-last-frame transition

**Route:** FLF.  
Prompt the continuous bridge: object path, body motion, material morph, camera path, environmental continuity and easing into final frame.

## 31. First-middle-last sequence

**Route:** FML guider.  
Use when the midpoint is compositionally mandatory. Describe two transitions separately and ensure the middle anchor is reachable.

## 32. Seamless loop

**Route:** loop workflow.  
Choose cyclical actions: breathing, rotating object, wave, pendulum, walking cycle, light pulse. Final phase must match initial phase.

## 33. Long-video continuation

**Route:** extension.  
Use last stable frame/latent as new anchor. Prompt only the next action. Maintain identity/style/audio continuity externally and expect drift to accumulate.

## 34. Shot-to-shot transition

**Route:** V2V transition LoRA/workflow.  
Define visual bridge: whip pan, object wipe, match shape, light flash, foreground occlusion, or material dissolve. Preserve each endpoint outside transition window.

## 35. Viewpoint change

**Route:** cross-view/camera control workflow.  
State target angle and preserve subject geometry/identity. Use modest angle changes unless strong 3D references exist.

## 36. Outpaint/reframe

**Route:** outpainting IC-LoRA.  
Preserve central source region; describe newly revealed surroundings, perspective, light continuation and aspect target. Avoid altering the protected subject.

## 37. Add/remove/replace object

**Route:** V2V inpaint/EditAnything with mask.  
Specify mask target, replacement appearance, motion following, shadows/reflections/occlusion and preserve list.

## 38. Remove person/crowd cleanup

**Route:** masked V2V removal workflow.  
Describe reconstructed background and temporal texture. Preserve camera and remaining subjects.

## 39. Restyle video

**Route:** V2V + style LoRA.  
Preserve motion/timing/composition, change medium/material/palette. Avoid asking style change to rewrite the entire scene.

## 40. Day-to-night/colorization/HDR/deblur

**Route:** corresponding effect/restoration LoRA or workflow.  
Prompt target illumination/color and preserve geometry/timing. Let restoration nodes own technical correction.

## 41. Water/liquid simulation

**Route:** specialized LoRA/workflow when available.  
Define source, direction, viscosity, gravity, contact surfaces and splash/recovery. Keep one principal fluid event.

## 42. Ingredient/assembly animation

**Route:** Prompt Relay + effect workflow.  
Stage components entering, aligning and assembling. Use endpoint frame when final product geometry must be exact.

## 43. Meme/comedy short

**Route:** I2V/T2V + Relay.  
Set up → pause → one visual reversal → reaction. Timing and silence matter more than extra detail.

## 44. Vertical social ad

**Route:** native portrait/I2V/T2V.  
Keep hero subject centered within safe area; fast readable opening action; one benefit reveal; final hold for post text. Avoid generating small typography.

## 45. Cinematic trailer montage

**Route:** generate separate shots and edit; do not force unrelated montage into one prompt.  
Create a shot list with a shared style/identity bible. Prompt each shot independently, then assemble with music and transitions.

## 46. Character consistency series

**Route:** character sheet + ID-LoRA/trained LoRA + fixed style bible.  
Maintain a continuity record: face, hair, wardrobe, age, proportions, props, color palette, voice, environment rules. Each shot prompt includes only relevant reminders.

## 47. Multi-subject reference

**Route:** multi-reference workflow.  
Assign each reference a stable label and screen position. Start with simple actions and avoid occlusion/crossing until identity is proven.

## 48. Camera-only test

**Route:** I2V + camera control.  
Subject remains nearly still; test one dolly/pan/orbit/jib path. This isolates camera adherence before adding action/dialogue.

## 49. Motion-only test

**Route:** I2V/pose control.  
Lock camera and background; test one body/object action. Useful for diagnosing whether failure is motion or camera complexity.

## 50. Prompt A/B evaluation

Keep seed, workflow, checkpoint, resolution, duration, references, audio and controls fixed. Compare only:

- action wording,
- camera wording,
- temporal segmentation,
- speaker labels,
- preservation constraints.

Score identity, motion, camera, temporal order, audio sync, dialogue ownership, artifacts and overall usefulness separately.
