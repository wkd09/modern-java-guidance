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


def _resolve_maven_prop(raw: str | None, props: dict[str, str]) -> str | None:
    if not raw:
        return None
    val = raw.strip()
    m = re.fullmatch(r"\$\{([^}]+)\}", val)
    if m:
        return props.get(m.group(1).strip())
    return val


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

    # Pass 1: collect <properties> so ${...} placeholders resolve reliably
    props: dict[str, str] = {}
    for elem in root.iter():
        if strip_ns(elem.tag) == "properties":
            for child in elem:
                if child.text and child.text.strip():
                    props[strip_ns(child.tag)] = child.text.strip()

    for key in ("java.version", "maven.compiler.release", "maven.compiler.source", "maven.compiler.target"):
        if key in props:
            parsed = _parse_java_int(_resolve_maven_prop(props[key], props))
            if parsed is not None:
                java_ver = parsed
                break

    for boot_prop in ("spring-boot.version", "spring.boot.version"):
        if boot_prop in props:
            parsed_boot = _parse_boot_tuple(_resolve_maven_prop(props[boot_prop], props))
            if parsed_boot is not None:
                boot_ver = parsed_boot
                break

    # Pass 2: inspect <parent>, <dependency> (including BOM in <dependencyManagement>), and compiler config
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
                parsed_boot = _parse_boot_tuple(_resolve_maven_prop(version, props))
                if parsed_boot is not None:
                    boot_ver = parsed_boot
        elif tag == "dependency" and boot_ver is None:
            artifact_id = None
            version = None
            for child in elem:
                ctag = strip_ns(child.tag)
                if ctag == "artifactId":
                    artifact_id = child.text.strip() if child.text else None
                elif ctag == "version":
                    version = child.text
            if artifact_id in {"spring-boot-dependencies", "spring-boot-starter-parent"} and version:
                parsed_boot = _parse_boot_tuple(_resolve_maven_prop(version, props))
                if parsed_boot is not None:
                    boot_ver = parsed_boot
        elif tag in {"release", "source", "target"} and java_ver is None:
            parsed = _parse_java_int(_resolve_maven_prop(elem.text, props))
            if parsed is not None:
                java_ver = parsed

    return ProjectProfile(java_ver, boot_ver, str(pom_path), uses_security)


def _detect_from_version_catalog(toml_path: Path) -> ProjectProfile:
    text = toml_path.read_text(encoding="utf-8", errors="replace")
    uses_security = "spring-boot-starter-security" in text or "spring-security" in text
    java_ver: int | None = None
    boot_ver: tuple[int, int, int] | None = None

    m_boot = re.search(
        r"(?:^|\n)\s*spring[-_]?boot(?:[-_]?version)?\s*=\s*['\"]([^'\"]+)['\"]",
        text,
        re.IGNORECASE,
    )
    if m_boot:
        boot_ver = _parse_boot_tuple(m_boot.group(1))

    m_java = re.search(
        r"(?:^|\n)\s*(?:java(?:[-_]?version)?|jdk(?:[-_]?version)?)\s*=\s*['\"]?([^'\"\n]+)['\"]?",
        text,
        re.IGNORECASE,
    )
    if m_java:
        java_ver = _parse_java_int(m_java.group(1))

    return ProjectProfile(java_ver, boot_ver, str(toml_path), uses_security)


def _detect_from_gradle(gradle_path: Path) -> ProjectProfile:
    text = gradle_path.read_text(encoding="utf-8", errors="replace")
    uses_security = "spring-boot-starter-security" in text or "spring-security" in text
    java_ver: int | None = None
    boot_ver: tuple[int, int, int] | None = None

    # Java toolchain / sourceCompatibility / JavaVersion.VERSION_1_8 / VERSION_21
    patterns = [
        r"JavaLanguageVersion\.of\(\s*(\d+)\s*\)",
        r"JavaVersion\.VERSION_(?:1_)?(\d+)",
        r"(?:sourceCompatibility|targetCompatibility)\s*=\s*['\"]?(?:1\.)?(\d+)['\"]?",
        r"jvmToolchain\(\s*(\d+)\s*\)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            java_ver = _parse_java_int(m.group(1))
            if java_ver is not None:
                break

    # Spring Boot plugin or BOM version
    boot_patterns = [
        r"id\s*\(\s*['\"]org\.springframework\.boot['\"]\s*\)\s*version\s*['\"]([^'\"]+)['\"]",
        r"id\s+['\"]org\.springframework\.boot['\"]\s+version\s*['\"]([^'\"]+)['\"]",
        r"org\.springframework\.boot:spring-boot-dependencies:([^\s'\"]+)",
    ]
    for pat in boot_patterns:
        m = re.search(pat, text)
        if m:
            boot_ver = _parse_boot_tuple(m.group(1))
            if boot_ver is not None:
                break

    toml_path = gradle_path.parent / "gradle" / "libs.versions.toml"
    if toml_path.is_file():
        cat = _detect_from_version_catalog(toml_path)
        if boot_ver is None:
            boot_ver = cat.spring_boot_version
        if java_ver is None:
            java_ver = cat.java_version
        uses_security = uses_security or cat.uses_spring_security

    return ProjectProfile(java_ver, boot_ver, str(gradle_path), uses_security)


def detect_project(start_path: Path) -> ProjectProfile:
    """Walk upward from start_path, merging versions across multi-module build files."""
    current = start_path.resolve()
    if current.is_file():
        current = current.parent

    java_ver: int | None = None
    boot_ver: tuple[int, int, int] | None = None
    uses_security = False
    source_file: str | None = None

    def _merge(candidate: ProjectProfile) -> None:
        nonlocal java_ver, boot_ver, uses_security, source_file
        if source_file is None:
            source_file = candidate.source_file
        if java_ver is None and candidate.java_version is not None:
            java_ver = candidate.java_version
            if source_file is None:
                source_file = candidate.source_file
        if boot_ver is None and candidate.spring_boot_version is not None:
            boot_ver = candidate.spring_boot_version
            if source_file is None:
                source_file = candidate.source_file
        uses_security = uses_security or candidate.uses_spring_security

    for directory in [current, *current.parents]:
        pom = directory / "pom.xml"
        if pom.is_file():
            _merge(_detect_from_pom(pom))

        for gradle_name in ("build.gradle.kts", "build.gradle"):
            gradle = directory / gradle_name
            if gradle.is_file():
                _merge(_detect_from_gradle(gradle))

        toml = directory / "gradle" / "libs.versions.toml"
        if toml.is_file() and (java_ver is None or boot_ver is None):
            _merge(_detect_from_version_catalog(toml))

        java_ver_file = directory / ".java-version"
        if java_ver_file.is_file() and java_ver is None:
            jv = _parse_java_int(java_ver_file.read_text(encoding="utf-8", errors="replace"))
            if jv is not None:
                _merge(ProjectProfile(jv, None, str(java_ver_file)))

        if java_ver is not None and boot_ver is not None:
            return ProjectProfile(java_ver, boot_ver, source_file, uses_security)

        if (directory / ".git").exists():
            break

    return ProjectProfile(java_ver, boot_ver, source_file, uses_security)
