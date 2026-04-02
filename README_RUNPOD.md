# Wan Pipeline RunPod API Guide

This guide documents the unified RunPod Serverless API for `wan-pipeline-master`.

Supported modes:
- `image`
- `t2v`
- `i2v`
- `first_last`
- `animate`
- `replace`

---

## 1) Endpoint and auth

Set these once:

```bash
export RUNPOD_API_KEY="YOUR_RUNPOD_API_KEY"
export ENDPOINT_ID="yatvfdmrmgdd1g"
export RUNPOD_URL="https://api.runpod.ai/v2/${ENDPOINT_ID}/run"
```

All requests use:
- `POST ${RUNPOD_URL}`
- `Authorization: Bearer ${RUNPOD_API_KEY}`
- JSON body with top-level `input`

---

## 2) Quick capability check

```bash
curl -X POST "${RUNPOD_URL}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -d '{"input":{"aleef":true}}'
```

This returns service metadata and available modes.

---

## 3) Environment variables (RunPod endpoint)

### Required for S3 output/input routing

Single-bucket mode:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `OUTPUT_S3_BUCKET`
- `AWS_REGION` (recommended: `us-east-2`)

Or split mode:
- `STAG_AWS_ACCESS_KEY_ID`
- `STAG_AWS_SECRET_ACCESS_KEY`
- `STAG_S3_BUCKET`
- `PROD_AWS_ACCESS_KEY_ID`
- `PROD_AWS_SECRET_ACCESS_KEY`
- `PROD_S3_BUCKET`
- `AWS_REGION`

### Model loading behavior

- `WAN_LOCAL_MODELS_ONLY=1` -> local-only model load, fail if missing.
- `WAN_LOCAL_MODELS_ONLY=0` -> local-first, fallback to HF download.
- `MODEL_ROOT` default: `/runpod-volume/models`

Optional explicit paths:
- `T2V_MODEL_PATH`
- `I2V_MODEL_PATH`
- `I2V_FIRST_LAST_MODEL_PATH`
- `ANIMATE_MODEL_PATH`

---

## 4) Input source paths

File paths in payload may be:
- `s3://bucket/key`
- `https://...`
- local path (debug only)

Outputs are uploaded to S3 and returned as:
- `video_path` / `image_path` (`s3://...`)
- `video_url` / `image_url` (presigned URL)

---

## 5) API examples by mode

## 5.1 `image` (text-to-image)

```bash
curl -X POST "${RUNPOD_URL}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -d '{
    "input": {
      "mode": "image",
      "prompt": "Cinematic portrait, natural lighting, highly detailed",
      "width": 720,
      "height": 1280,
      "quality_preset": "high",
      "num_inference_steps": 40,
      "guidance_scale": 4.0,
      "guidance_scale_2": 3.0,
      "level": "stag"
    }
  }'
```

`quality_preset`: `fast|balanced|high|ultra`

---

## 5.2 `t2v` (text-to-video)

```bash
curl -X POST "${RUNPOD_URL}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -d '{
    "input": {
      "mode": "t2v",
      "prompt": "A cinematic golden-hour drone orbit around a cliffside villa",
      "resolution": "720p",
      "duration_seconds": 5,
      "quality_preset": "max",
      "num_inference_steps": 80,
      "guidance_scale": 4.0,
      "guidance_scale_2": 3.0,
      "level": "stag"
    }
  }'
```

`quality_preset`: `fast|balanced|high|ultra|max`

---

## 5.3 `i2v` (image-to-video)

```bash
curl -X POST "${RUNPOD_URL}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -d '{
    "input": {
      "mode": "i2v",
      "img_path": "s3://YOUR_BUCKET/path/to/input_image.png",
      "prompt": "Natural realistic motion with cinematic detail",
      "resolution": "720p",
      "duration_seconds": 5,
      "quality_preset": "ultra",
      "use_lightning_loras": false,
      "num_inference_steps": 64,
      "guidance_scale": 1.2,
      "level": "stag"
    }
  }'
```

`quality_preset`: `fast|balanced|high|ultra`

---

## 5.4 `first_last` (start/end frame transition)

```bash
curl -X POST "${RUNPOD_URL}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -d '{
    "input": {
      "mode": "first_last",
      "start_image_path": "s3://YOUR_BUCKET/first_last/start.png",
      "end_image_path": "s3://YOUR_BUCKET/first_last/end.png",
      "prompt": "Smooth cinematic transition",
      "duration_seconds": 5,
      "quality_preset": "high",
      "num_inference_steps": 20,
      "guidance_scale": 1.2,
      "guidance_scale_2": 1.2,
      "shift": 8.0,
      "seed": 42,
      "level": "stag"
    }
  }'
```

`quality_preset`: `fast|balanced|high|ultra`

---

## 5.5 `animate` (character animation)

```bash
curl -X POST "${RUNPOD_URL}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -d '{
    "input": {
      "mode": "animate",
      "prompt": "People in the video are doing actions.",
      "ref_image_path": "s3://YOUR_BUCKET/animate/src_ref.png",
      "pose_video_path": "s3://YOUR_BUCKET/animate/src_pose.mp4",
      "face_video_path": "s3://YOUR_BUCKET/animate/src_face.mp4",
      "quality_preset": "high",
      "num_inference_steps": 28,
      "guidance_scale": 1.0,
      "segment_frame_length": 77,
      "prev_segment_conditioning_frames": 1,
      "fps": 30,
      "seed": 123,
      "level": "stag"
    }
  }'
```

`quality_preset`: `fast|balanced|high|ultra`

---

## 5.6 `replace` (character replacement)

```bash
curl -X POST "${RUNPOD_URL}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -d '{
    "input": {
      "mode": "replace",
      "prompt": "People in the video are doing actions.",
      "ref_image_path": "s3://YOUR_BUCKET/replace/src_ref.png",
      "pose_video_path": "s3://YOUR_BUCKET/replace/src_pose.mp4",
      "face_video_path": "s3://YOUR_BUCKET/replace/src_face.mp4",
      "background_video_path": "s3://YOUR_BUCKET/replace/src_bg.mp4",
      "mask_video_path": "s3://YOUR_BUCKET/replace/src_mask.mp4",
      "quality_preset": "high",
      "num_inference_steps": 28,
      "guidance_scale": 1.0,
      "segment_frame_length": 77,
      "prev_segment_conditioning_frames": 1,
      "fps": 30,
      "seed": 123,
      "level": "stag"
    }
  }'
```

`quality_preset`: `fast|balanced|high|ultra`

---

## 6) Typical success response

Video modes (`t2v`, `i2v`, `first_last`, `animate`, `replace`) return fields like:
- `video_path`
- `video_url`
- mode/quality/inference metadata
- `latency_seconds`

Image mode returns:
- `image_path`
- `image_url`
- width/height and quality metadata

---

## 7) Typical error response

```json
{
  "error": "human-readable reason"
}
```

Examples:
- missing required inputs
- unsupported mode
- missing local model (when `WAN_LOCAL_MODELS_ONLY=1`)
- download/decode failures

---

## 8) Practical test strategy

1. Run `aleef` check first.
2. Test `image` and `t2v`.
3. Test `i2v`.
4. Test `first_last`.
5. Test `animate`, then `replace`.

For first tests, keep clips short (3-6s) and use lower steps, then raise quality settings.

