"""Detect Java and Spring Boot versions from project build files."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class ProjectProfile:
    java_version: int | None
    spring_boot_version: tuple[int, int, int] | None
    source_file: str | None
    uses_spring_security: bool = False

    @property
    def effective_java(self) -> int:
        return self.java_version if self.java_version is not None else 21

    @property
    def effective_boot(self) -> tuple[int, int, int] | None:
        return self.spring_boot_version

    def to_dict(self) -> dict[str, object]:
        return {
            "java_version": self.java_version,
            "effective_java": self.effective_java,
            "spring_boot_version": (
                ".".join(map(str, self.spring_boot_version))
                if self.spring_boot_version
                else None
            ),
            "source_file": self.source_file,
            "uses_spring_security": self.uses_spring_security,
        }


def _parse_java_int(raw: str | None) -> int | None:
    if not raw:
        return None
    cleaned = raw.strip().strip("\"'")
    if cleaned.startswith("1."):
        cleaned = cleaned[2:]
    m = re.search(r"(\d+)", cleaned)
    if not m:
        return None
    val = int(m.group(1))
    return val if 6 <= val <= 30 else None


def _parse_boot_tuple(raw: str | None) -> tuple[int, int, int] | None:
    if not raw:
        return None
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", raw.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def _detect_from_pom(pom_path: Path) -> ProjectProfile:
    text = pom_path.read_text(encoding="utf-8", errors="replace")
    uses_security = "spring-boot-starter-security" in text or "spring-security" in text
    java_ver: int | None = None
    boot_ver: tuple[int, int, int] | None = None

    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return ProjectProfile(None, None, str(pom_path), uses_security)

    def strip_ns(tag: str) -> str:
        return tag.split("}", 1)[-1]

    # Check parent for spring-boot-starter-parent
    for elem in root.iter():
        tag = strip_ns(elem.tag)
        if tag == "parent":
            artifact_id = None
            version = None
            for child in elem:
                ctag = strip_ns(child.tag)
                if ctag == "artifactId":
                    artifact_id = child.text
                elif ctag == "version":
                    version = child.text
            if artifact_id and "spring-boot" in artifact_id and version:
                boot_ver = _parse_boot_tuple(version)
        elif tag == "properties":
            for child in elem:
                ptag = strip_ns(child.tag)
                if ptag in {"java.version", "maven.compiler.release", "maven.compiler.source", "maven.compiler.target"}:
                    parsed = _parse_java_int(child.text)
                    if parsed is not None:
                        java_ver = parsed
                elif ptag == "spring-boot.version" and boot_ver is None:
                    boot_ver = _parse_boot_tuple(child.text)
        elif tag in {"release", "source", "target"} and java_ver is None:
            parsed = _parse_java_int(elem.text)
            if parsed is not None:
                java_ver = parsed

    return ProjectProfile(java_ver, boot_ver, str(pom_path), uses_security)


def _detect_from_gradle(gradle_path: Path) -> ProjectProfile:
    text = gradle_path.read_text(encoding="utf-8", errors="replace")
    uses_security = "spring-boot-starter-security" in text or "spring-security" in text
    java_ver: int | None = None
    boot_ver: tuple[int, int, int] | None = None

    # Java toolchain / sourceCompatibility / JavaVersion.VERSION_21
    patterns = [
        r"JavaLanguageVersion\.of\(\s*(\d+)\s*\)",
        r"JavaVersion\.VERSION_(\d+)",
        r"sourceCompatibility\s*=\s*['\"]?(?:1\.)?(\d+)['\"]?",
        r"jvmToolchain\(\s*(\d+)\s*\)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            java_ver = _parse_java_int(m.group(1))
            if java_ver is not None:
                break

    # Spring Boot plugin version
    boot_patterns = [
        r"id\s*\(\s*['\"]org\.springframework\.boot['\"]\s*\)\s*version\s*['\"]([^'\"]+)['\"]",
        r"id\s+['\"]org\.springframework\.boot['\"]\s+version\s+['\"]([^'\"]+)['\"]",
        r"org\.springframework\.boot:spring-boot-dependencies:([^\s'\"]+)",
    ]
    for pat in boot_patterns:
        m = re.search(pat, text)
        if m:
            boot_ver = _parse_boot_tuple(m.group(1))
            if boot_ver is not None:
                break

    # Check gradle/libs.versions.toml if boot_ver still None
    toml_path = gradle_path.parent / "gradle" / "libs.versions.toml"
    if boot_ver is None and toml_path.is_file():
        toml_text = toml_path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"spring[-_]boot\s*=\s*['\"]([^'\"]+)['\"]", toml_text, re.IGNORECASE)
        if m:
            boot_ver = _parse_boot_tuple(m.group(1))

    return ProjectProfile(java_ver, boot_ver, str(gradle_path), uses_security)


def detect_project(start_path: Path) -> ProjectProfile:
    """Walk upward from start_path to locate pom.xml or build.gradle(.kts)."""
    current = start_path.resolve()
    if current.is_file():
        current = current.parent

    for directory in [current, *current.parents]:
        pom = directory / "pom.xml"
        if pom.is_file():
            return _detect_from_pom(pom)

        for gradle_name in ("build.gradle.kts", "build.gradle"):
            gradle = directory / gradle_name
            if gradle.is_file():
                return _detect_from_gradle(gradle)

        java_ver_file = directory / ".java-version"
        if java_ver_file.is_file():
            jv = _parse_java_int(java_ver_file.read_text(encoding="utf-8", errors="replace"))
            if jv is not None:
                return ProjectProfile(jv, None, str(java_ver_file))

        if (directory / ".git").exists():
            break

    return ProjectProfile(None, None, None)
