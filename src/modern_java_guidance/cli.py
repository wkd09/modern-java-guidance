"""CLI entry point for modern-java-guidance (`mjg`)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from modern_java_guidance import __version__
from modern_java_guidance.detector import ProjectProfile, _parse_boot_tuple, detect_project
from modern_java_guidance.exporters import export_semgrep_yaml
from modern_java_guidance.guides import retrieve_guide, search_guides
from modern_java_guidance.hook import run_hook
from modern_java_guidance.scanner import scan_target


def _resolve_skill_source() -> Path | None:
    """Locate the modern-java-guidance skill directory (repo checkout or wheel-bundled copy)."""
    pkg_bundled = Path(__file__).resolve().parent / "bundled_skill"
    repo_skill = Path(__file__).resolve().parent.parent.parent / "skills" / "modern-java-guidance"
    for candidate in (repo_skill, pkg_bundled):
        if (candidate / "SKILL.md").is_file():
            return candidate
    return None


def _apply_profile_overrides(
    profile: ProjectProfile,
    java_override: int | None,
    boot_override: str | None,
) -> ProjectProfile | None:
    if java_override is None and boot_override is None:
        return profile
    java_ver = java_override if java_override is not None else profile.java_version
    if boot_override is not None:
        boot_ver = _parse_boot_tuple(boot_override)
        if boot_ver is None:
            print(
                f"Error: invalid --boot version '{boot_override}'. Expected format like '3.3.0' or '3.4'.",
                file=sys.stderr,
            )
            return None
    else:
        boot_ver = profile.spring_boot_version
    return ProjectProfile(java_ver, boot_ver, profile.source_file, profile.uses_spring_security)


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

    profile = _apply_profile_overrides(detect_project(target), args.java, args.boot)
    if profile is None:
        return 2

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
    code, stdout_json, stderr_msg = run_hook(args.format, strict=args.strict)
    if stdout_json:
        print(stdout_json)
    if stderr_msg:
        print(stderr_msg, file=sys.stderr)
    return code


def _cmd_search(args: argparse.Namespace) -> int:
    matches = search_guides(args.query)
    if args.json:
        print(json.dumps([m.to_dict() for m in matches], indent=2))
        return 0
    if not matches:
        print(f"No guides matched '{args.query}'.")
        return 1
    for m in matches:
        gate = f"Java {m.min_java}+" + (f", Boot {m.min_boot}+" if m.min_boot else "")
        print(f"{m.guide_id:<8} [{gate}] {m.title}")
        print(f"         {m.summary}")
    return 0


def _cmd_retrieve(args: argparse.Namespace) -> int:
    entry = retrieve_guide(args.guide_id)
    if entry is None:
        print(f"Error: unknown guide ID '{args.guide_id}'. Run 'mjg search' to list guides.", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(entry.to_dict(), indent=2))
        return 0

    gate = f"Java {entry.min_java}+" + (f", Spring Boot {entry.min_boot}+" if entry.min_boot else "")
    print(f"# {entry.guide_id}: {entry.title} ({gate})")
    print(f"\n{entry.summary}\n")
    print("## Before (Legacy)")
    print(entry.before_code)
    print("\n## After (Modern)")
    print(entry.after_code)
    print(f"\n## Caveat\n{entry.caveat}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    profile = _apply_profile_overrides(detect_project(Path(args.path)), args.java, args.boot)
    if profile is None:
        return 2

    content = export_semgrep_yaml(profile)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        print(f"Exported {args.format} rules -> {out_path}")
    else:
        print(content, end="")
    return 0


def _copy_skill(skill_src: Path, dest_dir: Path) -> None:
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_src, dest_dir)


def _cmd_setup(args: argparse.Namespace) -> int:
    skill_src = _resolve_skill_source()
    project_dir = Path(args.dir).resolve()

    if skill_src is None:
        print(
            "Warning: bundled skill assets not found; hooks will be configured without copying SKILL.md.",
            file=sys.stderr,
        )

    if args.target in ("antigravity", "all"):
        if skill_src is not None:
            global_skill = (
                Path(args.skill_dir).resolve()
                if args.skill_dir
                else Path.home() / ".gemini" / "config" / "skills" / "modern-java-guidance"
            )
            _copy_skill(skill_src, global_skill)
            print(f"Installed Antigravity skill -> {global_skill}")

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
                    "matcher": "write_file|edit_file|write_to_file|replace_file_content|multi_replace_file_content",
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
        if skill_src is not None:
            claude_skill = project_dir / ".claude" / "skills" / "modern-java-guidance"
            _copy_skill(skill_src, claude_skill)
            print(f"Installed Claude Code skill -> {claude_skill}")

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
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_detect = sub.add_parser("detect", help="Detect Java and Spring Boot versions in a project.")
    p_detect.add_argument("path", nargs="?", default=".", help="Project path (default: .)")
    p_detect.add_argument("--json", action="store_true", help="Output JSON")
    p_detect.set_defaults(func=_cmd_detect)

    p_check = sub.add_parser("check", help="Scan .java and Boot config file(s) for legacy patterns.")
    p_check.add_argument("target", help="File or directory to scan")
    p_check.add_argument("--java", type=int, help="Override detected Java version")
    p_check.add_argument("--boot", type=str, help="Override detected Spring Boot version (e.g. 3.4.0)")
    p_check.add_argument("--json", action="store_true", help="Output JSON")
    p_check.add_argument("--strict", action="store_true", help="Exit non-zero on warnings/info too")
    p_check.set_defaults(func=_cmd_check)

    p_hook = sub.add_parser("hook", help="Run as a PostToolUse hook reading JSON from stdin.")
    p_hook.add_argument("--format", choices=("antigravity", "claude"), default="antigravity")
    p_hook.add_argument("--strict", action="store_true", help="Block Claude Code on warnings/info as well as errors")
    p_hook.set_defaults(func=_cmd_hook)

    p_search = sub.add_parser("search", help="Search modern Java/Spring Boot pattern guides by keyword.")
    p_search.add_argument("query", nargs="?", default="", help="Search keywords (omit to list all)")
    p_search.add_argument("--json", action="store_true", help="Output JSON")
    p_search.set_defaults(func=_cmd_search)

    p_retrieve = sub.add_parser("retrieve", help="Retrieve full Before/After guide by ID (e.g. BOOT-002).")
    p_retrieve.add_argument("guide_id", help="Guide ID (e.g. JAVA-010, BOOT-002)")
    p_retrieve.add_argument("--json", action="store_true", help="Output JSON")
    p_retrieve.set_defaults(func=_cmd_retrieve)

    p_export = sub.add_parser("export", help="Export version-gated rules to external static analysis tools.")
    p_export.add_argument("--format", choices=("semgrep",), default="semgrep", help="Target format (default: semgrep)")
    p_export.add_argument("--path", default=".", help="Project path for auto-detecting versions (default: .)")
    p_export.add_argument("--java", type=int, help="Override detected Java version")
    p_export.add_argument("--boot", type=str, help="Override detected Spring Boot version (e.g. 3.4.0)")
    p_export.add_argument("-o", "--output", type=str, help="Write exported rules to file instead of stdout")
    p_export.set_defaults(func=_cmd_export)

    p_setup = sub.add_parser("setup", help="Install skill files and configure PostToolUse hooks.")
    p_setup.add_argument("--target", choices=("antigravity", "claude", "all"), default="antigravity")
    p_setup.add_argument("--dir", default=".", help="Target project directory for hooks/skills")
    p_setup.add_argument("--skill-dir", type=str, help="Override Antigravity skill install destination")
    p_setup.set_defaults(func=_cmd_setup)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
