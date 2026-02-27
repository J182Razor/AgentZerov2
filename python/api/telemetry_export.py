"""Telemetry export API — JSON and Prometheus formats."""
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
