from dataclasses import dataclass
from typing import Any

LIVE_STATUS_PROMPT_VERSION = "ai-live-status-v1"
COMPARISON_REPORT_PROMPT_VERSION = "ai-comparison-report-v1"
PROVIDER_HEALTH_PROMPT_VERSION = "ai-provider-health-v1"


@dataclass(frozen=True)
class LiveStatusPrompt:
    version: str
    system_message: str
    input_payload: dict[str, Any]
    response_schema: dict[str, Any]


@dataclass(frozen=True)
class ComparisonReportPrompt:
    version: str
    system_message: str
    input_payload: dict[str, Any]
    response_schema: dict[str, Any]


@dataclass(frozen=True)
class ProviderHealthPrompt:
    version: str
    system_message: str
    input_payload: dict[str, Any]
    response_schema: dict[str, Any]


def build_live_status_prompt(input_payload: dict[str, Any]) -> LiveStatusPrompt:
    return LiveStatusPrompt(
        version=LIVE_STATUS_PROMPT_VERSION,
        system_message=(
            "You are an AI-assisted advisory analyst for a paper-only betting research "
            "system. Explain live process state using only the supplied structured input. "
            "Do not recommend real-money betting, bookmaker account automation, safety "
            "gate bypasses, proxy use, or CAPTCHA bypass. Return concise structured JSON."
        ),
        input_payload=input_payload,
        response_schema={
            "type": "object",
            "required": [
                "label",
                "short_summary",
                "root_cause",
                "risk_flags",
                "recommended_next_actions",
                "confidence",
                "source_record_ids",
            ],
            "properties": {
                "label": {"type": "string"},
                "short_summary": {"type": "string"},
                "root_cause": {"type": "string"},
                "risk_flags": {"type": "array", "items": {"type": "string"}},
                "recommended_next_actions": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                "source_record_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
    )


def build_comparison_report_prompt(input_payload: dict[str, Any]) -> ComparisonReportPrompt:
    return ComparisonReportPrompt(
        version=COMPARISON_REPORT_PROMPT_VERSION,
        system_message=(
            "You are an AI-assisted advisory analyst for paper-only betting model "
            "research. Explain comparison results from structured report data. Prefer "
            "calibration evidence over ROI-only conclusions, identify sample-size risk, "
            "and recommend the next research experiment. Do not recommend real-money "
            "betting or bookmaker account automation. Return concise structured JSON."
        ),
        input_payload=input_payload,
        response_schema={
            "type": "object",
            "required": [
                "label",
                "short_summary",
                "root_cause",
                "risk_flags",
                "recommended_next_actions",
                "confidence",
                "source_record_ids",
            ],
            "properties": {
                "label": {"type": "string"},
                "short_summary": {"type": "string"},
                "root_cause": {"type": "string"},
                "risk_flags": {"type": "array", "items": {"type": "string"}},
                "recommended_next_actions": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                "source_record_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
    )


def build_provider_health_prompt(input_payload: dict[str, Any]) -> ProviderHealthPrompt:
    return ProviderHealthPrompt(
        version=PROVIDER_HEALTH_PROMPT_VERSION,
        system_message=(
            "You are an AI-assisted advisory analyst for live provider health in a "
            "paper-only betting research system. Explain provider validation failures, "
            "identify fail closed safety behavior, and recommend next engineering actions. "
            "Do not recommend real-money betting, bookmaker account automation, proxy use, "
            "or CAPTCHA bypass. Return concise structured JSON."
        ),
        input_payload=input_payload,
        response_schema={
            "type": "object",
            "required": [
                "label",
                "short_summary",
                "root_cause",
                "risk_flags",
                "recommended_next_actions",
                "confidence",
                "source_record_ids",
            ],
            "properties": {
                "label": {"type": "string"},
                "short_summary": {"type": "string"},
                "root_cause": {"type": "string"},
                "risk_flags": {"type": "array", "items": {"type": "string"}},
                "recommended_next_actions": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                "source_record_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
    )
