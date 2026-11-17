"""Post-Edit Hook handlers for Antigravity, Claude Code, and generic stdin JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from modern_java_guidance.detector import detect_project
from modern_java_guidance.scanner import Finding, scan_file


def extract_target_paths(payload: dict[str, object]) -> list[Path]:
    """Extract edited/created file paths from Antigravity or Claude Code hook payloads."""
    paths: list[Path] = []

    # Antigravity PostToolUse: {"toolCall": {"name": "...", "args": {"Path": "..." | "TargetFile": "..."}}}
    tool_call = payload.get("toolCall")
    if isinstance(tool_call, dict):
        args = tool_call.get("args")
        if isinstance(args, dict):
            for key in ("Path", "TargetFile", "path", "file_path", "target_file"):
                val = args.get(key)
                if isinstance(val, str) and val:
                    paths.append(Path(val))

    # Claude Code PostToolUse: {"tool_name": "Write"|"Edit", "tool_input": {"file_path": "..."}}
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("file_path", "path", "TargetFile", "Path"):
            val = tool_input.get(key)
            if isinstance(val, str) and val:
                paths.append(Path(val))

    # Fallback direct key
    direct = payload.get("file_path")
    if isinstance(direct, str) and direct:
        paths.append(Path(direct))

    # Deduplicate preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def format_findings_message(findings: list[Finding]) -> str:
    lines = ["[modern-java-guidance] Legacy Java / Spring Boot patterns detected:"]
    for f in findings:
        lines.append(
            f"- {f.file}:{f.line} [{f.rule_id}] ({f.severity}) {f.message} -> {f.modern_replacement}"
        )
    return "\n".join(lines)


def run_hook(hook_format: str, raw_stdin: str | None = None) -> tuple[int, str, str]:
    """Process stdin hook JSON and return (exit_code, stdout_json, stderr_msg)."""
    text = raw_stdin if raw_stdin is not None else sys.stdin.read()
    if not text.strip():
        return 0, "{}", ""

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return 0, "{}", ""

    if not isinstance(payload, dict):
        return 0, "{}", ""

    java_files = [p for p in extract_target_paths(payload) if p.suffix == ".java" and p.is_file()]
    if not java_files:
        return 0, "{}", ""

    all_findings: list[Finding] = []
    for jf in java_files:
        profile = detect_project(jf)
        all_findings.extend(scan_file(jf, profile))

    if not all_findings:
        return 0, "{}", ""

    summary = format_findings_message(all_findings)

    if hook_format == "claude":
        out = json.dumps(
            {
                "decision": "block",
                "reason": summary,
            },
            ensure_ascii=False,
        )
        return 0, out, ""

    # Antigravity PostToolUse expects "{}" on stdout; diagnostics go to stderr.
    return 0, "{}", summary
