"""CLI entry point for modern-java-guidance (`mjg`)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from modern_java_guidance.detector import ProjectProfile, _parse_boot_tuple, detect_project
from modern_java_guidance.hook import run_hook
from modern_java_guidance.scanner import scan_target


def _cmd_detect(args: argparse.Namespace) -> int:
    profile = detect_project(Path(args.path))
    if args.json:
        print(json.dumps(profile.to_dict(), indent=2))
    else:
        boot_str = ".".join(map(str, profile.spring_boot_version)) if profile.spring_boot_version else "none"
        java_str = str(profile.java_version) if profile.java_version is not None else f"auto-default ({profile.effective_java})"
        print(f"Java Version       : {java_str}")
        print(f"Spring Boot Version: {boot_str}")
        print(f"Spring Security    : {profile.uses_spring_security}")
        print(f"Detected From      : {profile.source_file or 'none'}")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    target = Path(args.target)
    if not target.exists():
        print(f"Error: target does not exist: {target}", file=sys.stderr)
        return 2

    profile = detect_project(target)
    if args.java is not None or args.boot is not None:
        java_ver = args.java if args.java is not None else profile.java_version
        boot_ver = _parse_boot_tuple(args.boot) if args.boot is not None else profile.spring_boot_version
        profile = ProjectProfile(java_ver, boot_ver, profile.source_file, profile.uses_spring_security)

    findings = scan_target(target, profile)
    if args.json:
        print(
            json.dumps(
                {
                    "profile": profile.to_dict(),
                    "findings": [f.to_dict() for f in findings],
                },
                indent=2,
            )
        )
    else:
        if not findings:
            print(f"[OK] No legacy Java/Spring Boot patterns found (Java {profile.effective_java}).")
        else:
            for f in findings:
                print(f"{f.file}:{f.line}: {f.severity} [{f.rule_id}] {f.message}")
                print(f"  Legacy : {f.legacy_snippet}")
                print(f"  Modern : {f.modern_replacement}")

    if args.strict and findings:
        return 1
    if any(f.severity == "error" for f in findings):
        return 1
    return 0


def _cmd_hook(args: argparse.Namespace) -> int:
    code, stdout_json, stderr_msg = run_hook(args.format)
    if stdout_json:
        print(stdout_json)
    if stderr_msg:
        print(stderr_msg, file=sys.stderr)
    return code


def _cmd_setup(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parent.parent.parent
    skill_src = repo_root / "skills" / "modern-java-guidance"
    project_dir = Path(args.dir).resolve()

    if args.target in ("antigravity", "all"):
        # 1. Install global Antigravity skill if bundled in repo
        global_skill = Path.home() / ".gemini" / "config" / "skills" / "modern-java-guidance"
        if skill_src.is_dir():
            if global_skill.exists():
                shutil.rmtree(global_skill)
            shutil.copytree(skill_src, global_skill)
            print(f"Installed Antigravity global skill -> {global_skill}")

        # 2. Write .agents/hooks.json in target project
        agents_dir = project_dir / ".agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        hooks_path = agents_dir / "hooks.json"
        hooks_data: dict[str, object] = {}
        if hooks_path.is_file():
            try:
                hooks_data = json.loads(hooks_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                hooks_data = {}
        hooks_data["modern-java-guidance"] = {
            "PostToolUse": [
                {
                    "matcher": "write_to_file|replace_file_content|multi_replace_file_content",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "mjg hook --format antigravity",
                            "timeout": 10,
                        }
                    ],
                }
            ]
        }
        hooks_path.write_text(json.dumps(hooks_data, indent=2) + "\n", encoding="utf-8")
        print(f"Configured Antigravity PostToolUse hook -> {hooks_path}")

    if args.target in ("claude", "all"):
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path = claude_dir / "settings.json"
        settings_data: dict[str, object] = {}
        if settings_path.is_file():
            try:
                settings_data = json.loads(settings_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                settings_data = {}
        hooks = settings_data.setdefault("hooks", {})
        if isinstance(hooks, dict):
            post_tool = hooks.setdefault("PostToolUse", [])
            if isinstance(post_tool, list):
                entry = {
                    "matcher": "Write|Edit|MultiEdit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "mjg hook --format claude",
                        }
                    ],
                }
                if entry not in post_tool:
                    post_tool.append(entry)
        settings_path.write_text(json.dumps(settings_data, indent=2) + "\n", encoding="utf-8")
        print(f"Configured Claude Code PostToolUse hook -> {settings_path}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mjg",
        description="Modern Java (21+) & Spring Boot (3.x+) detector, linter, and Post-Edit Hook.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_detect = sub.add_parser("detect", help="Detect Java and Spring Boot versions in a project.")
    p_detect.add_argument("path", nargs="?", default=".", help="Project path (default: .)")
    p_detect.add_argument("--json", action="store_true", help="Output JSON")
    p_detect.set_defaults(func=_cmd_detect)

    p_check = sub.add_parser("check", help="Scan .java file(s) for legacy Java/Spring Boot patterns.")
    p_check.add_argument("target", help="Java file or directory to scan")
    p_check.add_argument("--java", type=int, help="Override detected Java version")
    p_check.add_argument("--boot", type=str, help="Override detected Spring Boot version (e.g. 3.4.0)")
    p_check.add_argument("--json", action="store_true", help="Output JSON")
    p_check.add_argument("--strict", action="store_true", help="Exit non-zero on warnings too")
    p_check.set_defaults(func=_cmd_check)

    p_hook = sub.add_parser("hook", help="Run as a PostToolUse hook reading JSON from stdin.")
    p_hook.add_argument("--format", choices=("antigravity", "claude"), default="antigravity")
    p_hook.set_defaults(func=_cmd_hook)

    p_setup = sub.add_parser("setup", help="Install global skill and configure PostToolUse hooks.")
    p_setup.add_argument("--target", choices=("antigravity", "claude", "all"), default="antigravity")
    p_setup.add_argument("--dir", default=".", help="Target project directory for hooks config")
    p_setup.set_defaults(func=_cmd_setup)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
