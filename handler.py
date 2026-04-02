import logging
import os
import shutil
import tempfile
import time
from pathlib import Path

import runpod
import torch

from models.wan_model import WANModel
from utils.storage import configure_storage_env, download_to_local, upload_asset, upload_video

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_MODEL = None
FPS = 16
RESOLUTION_MAP = {
    "480p": (832, 480),
    "720p": (1280, 720),
}


def _to_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _get_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    log.info("Initializing WAN model wrapper")
    _MODEL = WANModel(device="cuda", instagirl_lora_path=None)
    _MODEL.load_model()
    return _MODEL


def _normalize_mode(value):
    mode = str(value or "i2v").strip().lower()
    aliases = {
        "i2v": "i2v",
        "image_to_video": "i2v",
        "image": "image",
        "t2i": "image",
        "text_to_image": "image",
        "first_last": "first_last",
        "first-last": "first_last",
        "i2v_first_last": "first_last",
        "t2v": "t2v",
        "text_to_video": "t2v",
    }
    return aliases.get(mode)


def handler(event):
    workdir = None
    try:
        inp = event.get("input", {})

        if inp.get("aleef") is True:
            return {
                "service": "wan-pipeline",
                "version": "phase-3",
                "status": "serverless-ready",
                "inputs": [
                    "mode",
                    "img_path",
                    "start_image_path",
                    "end_image_path",
                    "prompt",
                    "duration_seconds",
                    "resolution",
                    "use_lightning_loras",
                    "num_inference_steps",
                    "guidance_scale",
                    "guidance_scale_2",
                    "shift",
                    "seed",
                    "level",
                    "output_prefix",
                ],
                "modes": ["image", "i2v", "first_last", "t2v"],
            }

        mode = _normalize_mode(inp.get("mode"))
        if mode is None:
            return {"error": "mode must be one of: image, i2v, first_last, t2v"}

        prompt = inp.get("prompt")
        if mode in ("image", "i2v", "t2v") and (not prompt or not isinstance(prompt, str)):
            return {"error": "prompt is required"}

        level = inp.get("level", "stag")
        output_prefix = inp.get("output_prefix")

        try:
            output_bucket = configure_storage_env(level)
        except Exception as exc:
            return {"error": f"failed to configure storage env: {exc}"}

        workdir = tempfile.mkdtemp(prefix="wan_pipeline_")
        model = _get_model()
        t0 = time.time()
        if mode == "image":
            width = int(inp.get("width", 720))
            height = int(inp.get("height", 1280))
            local_output_path = os.path.join(workdir, "output.png")
            model.generate_single_frame_from_prompt(
                prompt=prompt,
                output_path=local_output_path,
                width=width,
                height=height,
            )
            upload_result = upload_asset(
                local_path=local_output_path,
                bucket=output_bucket,
                key_prefix=output_prefix or "image_gen/wan_pipeline_t2i",
                suffix=".png",
                content_type="image/png",
            )
            return {
                "image_path": upload_result["s3_uri"],
                "image_url": upload_result["presigned_url"],
                "width": width,
                "height": height,
                "latency_seconds": round(time.time() - t0, 2),
            }

        if mode == "t2v":
            duration_seconds = float(inp.get("duration_seconds", 5.0))
            duration_seconds = max(0.5, min(duration_seconds, 12.0))
            resolution = inp.get("resolution", "480p")
            if resolution not in RESOLUTION_MAP:
                return {"error": "resolution must be one of: 480p, 720p"}
            width, height = RESOLUTION_MAP[resolution]
            num_frames = int(round(duration_seconds * FPS))
            num_frames = max(5, min(num_frames, 121))
            local_output_path = os.path.join(workdir, "output.mp4")
            model.generate_video_from_prompt(
                prompt=prompt,
                output_path=local_output_path,
                width=width,
                height=height,
                num_frames=num_frames,
                fps=FPS,
            )
            upload_result = upload_video(
                local_output_path,
                output_bucket,
                output_prefix or "video_gen/wan_pipeline_t2v",
            )
            return {
                "video_path": upload_result["s3_uri"],
                "video_url": upload_result["presigned_url"],
                "duration_seconds": duration_seconds,
                "resolution": resolution,
                "latency_seconds": round(time.time() - t0, 2),
            }

        if mode == "first_last":
            start_image_path = inp.get("start_image_path")
            end_image_path = inp.get("end_image_path")
            if not start_image_path or not end_image_path:
                return {"error": "start_image_path and end_image_path are required for first_last mode"}
            prompt = prompt or "animate"
            duration_seconds = float(inp.get("duration_seconds", 5.0))
            duration_seconds = max(0.5, min(duration_seconds, 10.0))
            num_inference_steps = int(inp.get("num_inference_steps", 8))
            guidance_scale = float(inp.get("guidance_scale", 1.0))
            guidance_scale_2 = float(inp.get("guidance_scale_2", 1.0))
            shift = float(inp.get("shift", 8.0))
            seed = inp.get("seed")
            seed = None if seed is None else int(seed)

            start_ext = Path(start_image_path).suffix or ".png"
            end_ext = Path(end_image_path).suffix or ".png"
            local_start = os.path.join(workdir, f"start{start_ext}")
            local_end = os.path.join(workdir, f"end{end_ext}")
            local_output_path = os.path.join(workdir, "output.mp4")
            download_to_local(start_image_path, local_start)
            download_to_local(end_image_path, local_end)

            model.generate_video_from_first_last_frame(
                start_image_path=local_start,
                end_image_path=local_end,
                prompt=prompt,
                output_path=local_output_path,
                duration_seconds=duration_seconds,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                guidance_scale_2=guidance_scale_2,
                shift=shift,
                seed=seed,
            )
            upload_result = upload_video(
                local_output_path,
                output_bucket,
                output_prefix or "video_gen/wan_pipeline_first_last",
            )
            return {
                "video_path": upload_result["s3_uri"],
                "video_url": upload_result["presigned_url"],
                "duration_seconds": duration_seconds,
                "num_inference_steps": num_inference_steps,
                "seed": seed,
                "latency_seconds": round(time.time() - t0, 2),
            }

        img_path = inp.get("img_path")
        if not img_path or not isinstance(img_path, str):
            return {"error": "img_path is required for i2v mode (supports s3://, https://, or local path)"}
        duration_seconds = float(inp.get("duration_seconds", 5.0))
        duration_seconds = max(0.5, min(duration_seconds, 12.0))
        resolution = inp.get("resolution", "480p")
        if resolution not in ("480p", "720p"):
            return {"error": "resolution must be one of: 480p, 720p"}
        use_lightning_loras = _to_bool(inp.get("use_lightning_loras"), default=True)
        num_frames = int(round(duration_seconds * FPS))
        num_frames = max(5, min(num_frames, 121))

        source_ext = Path(img_path).suffix or ".png"
        local_input_path = os.path.join(workdir, f"input{source_ext}")
        local_output_path = os.path.join(workdir, "output.mp4")
        download_to_local(img_path, local_input_path)
        model.generate_video_from_image(
            image_path=local_input_path,
            prompt=prompt,
            output_path=local_output_path,
            num_frames=num_frames,
            fps=FPS,
            resolution=resolution,
            use_lightning_loras=use_lightning_loras,
        )
        upload_result = upload_video(
            local_output_path,
            output_bucket,
            output_prefix or "video_gen/wan_pipeline_i2v",
        )
        return {
            "video_path": upload_result["s3_uri"],
            "video_url": upload_result["presigned_url"],
            "duration_seconds": duration_seconds,
            "resolution": resolution,
            "use_lightning_loras": use_lightning_loras,
            "latency_seconds": round(time.time() - t0, 2),
        }
    except Exception as exc:
        log.exception("Generation failed")
        return {"error": str(exc)}
    finally:
        if workdir and os.path.isdir(workdir):
            shutil.rmtree(workdir, ignore_errors=True)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


runpod.serverless.start({"handler": handler})
