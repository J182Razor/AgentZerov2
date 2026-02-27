"""NVIDIA Role Management API — live model/key assignment without restart."""
import json
from flask import request, jsonify
from python.helpers.nvidia_router import NvidiaRouter, NvidiaRole, KNOWN_NVIDIA_MODELS


async def get_nvidia_roles():
    router = NvidiaRouter.instance()
    return jsonify({"roles": router.to_dict(), "known_models": KNOWN_NVIDIA_MODELS})


async def update_nvidia_roles():
    data = request.json or {}
    roles_data = data.get("roles", data)  # accept both {roles:{...}} and flat {role: cfg}
    router = NvidiaRouter.instance()
    router.from_dict(roles_data)
    router.save_to_config()
    return jsonify({"ok": True, "roles": router.to_dict()})


async def test_nvidia_role():
    """Make a minimal single-token call to validate a model + API key pair."""
    data = request.json or {}
    model = data.get("model", "")
    api_key = data.get("api_key", "")
    api_base = data.get("api_base", "https://integrate.api.nvidia.com/v1")

    if not model or not api_key:
        return jsonify({"ok": False, "error": "model and api_key required"}), 400

    try:
        import litellm
        response = await litellm.acompletion(
            model=f"openai/{model}",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=1,
            api_key=api_key,
            api_base=api_base,
        )
        return jsonify({"ok": True, "model": model})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 200  # 200 so UI gets JSON


async def list_nvidia_models():
    return jsonify({"models": KNOWN_NVIDIA_MODELS})
