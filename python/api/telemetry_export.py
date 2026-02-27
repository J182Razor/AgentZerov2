"""Telemetry export API — JSON, Prometheus, and Quota formats."""
from flask import request, jsonify, Response
from python.helpers.telemetry import TelemetryCollector


async def get_telemetry():
    """GET /api/telemetry — returns JSON telemetry summary."""
    collector = TelemetryCollector.instance()
    return jsonify(collector.to_dict())


async def get_telemetry_prometheus():
    """GET /api/telemetry/prometheus — returns Prometheus text format."""
    collector = TelemetryCollector.instance()
    return Response(collector.to_prometheus(), mimetype="text/plain; version=0.0.4")


async def get_quota():
    """GET /api/quota — returns per-model quota status from QuotaManager."""
    try:
        from python.helpers.quota_manager import QuotaManager
        return jsonify(QuotaManager.instance().to_dict())
    except Exception:
        return jsonify({})
