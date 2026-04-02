import runpod


def handler(event):
    inp = event.get("input", {})
    if inp.get("aleef") is True:
        return {
            "service": "wan-pipeline",
            "version": "phase-1",
            "status": "serverless-ready",
            "inputs": [],
        }

    return {
        "error": "Phase 1 scaffold only. Inference handlers are added in next phases."
    }


runpod.serverless.start({"handler": handler})
