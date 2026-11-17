"""Version-aware legacy pattern scanner for Java 17/21+ and Spring Boot 3.x+."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from modern_java_guidance.detector import ProjectProfile


@dataclass(slots=True, frozen=True)
class Finding:
    rule_id: str
    severity: str
    file: str
    line: int
    legacy_snippet: str
    message: str
    modern_replacement: str

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "legacy_snippet": self.legacy_snippet,
            "message": self.message,
            "modern_replacement": self.modern_replacement,
        }


@dataclass(slots=True, frozen=True)
class Rule:
    rule_id: str
    min_java: int
    min_boot: tuple[int, int, int] | None
    severity: str
    pattern: re.Pattern[str]
    message: str
    modern_replacement: str


RULES: tuple[Rule, ...] = (
    # --- Java 17+ Rules ---
    Rule(
        rule_id="JAVA-001",
        min_java=16,
        min_boot=None,
        severity="warning",
        pattern=re.compile(r"\bnew\s+(?:java\.util\.)?Date\s*\(\s*\)|new\s+SimpleDateFormat\s*\("),
        message="Legacy mutable date/time API detected.",
        modern_replacement="Use java.time (Instant.now(), LocalDate, ZonedDateTime, DateTimeFormatter).",
    ),
    Rule(
        rule_id="JAVA-002",
        min_java=16,
        min_boot=None,
        severity="warning",
        pattern=re.compile(r"Collections\.unmodifiable(?:List|Set|Map)\s*\(\s*Arrays\.asList\s*\("),
        message="Verbose pre-Java 9 unmodifiable collection boilerplate.",
        modern_replacement="Use List.of(...), Set.of(...), or Map.of(...).",
    ),
    Rule(
        rule_id="JAVA-003",
        min_java=16,
        min_boot=None,
        severity="info",
        pattern=re.compile(r"String\.format\s*\("),
        message="Static String.format(...) can be written more readably with Java 15+ .formatted(...).",
        modern_replacement="Use \"...\".formatted(args...).",
    ),
    # --- Java 21+ Rules ---
    Rule(
        rule_id="JAVA-010",
        min_java=21,
        min_boot=None,
        severity="warning",
        pattern=re.compile(r"Executors\.new(?:FixedThreadPool|CachedThreadPool)\s*\("),
        message="Platform thread pool used on Java 21+ for potentially I/O-bound concurrency.",
        modern_replacement="Prefer Executors.newVirtualThreadPerTaskExecutor() for I/O-bound workloads (keep bounded pools/semaphores only for CPU-bound or rate-limited tasks).",
    ),
    Rule(
        rule_id="JAVA-011",
        min_java=21,
        min_boot=None,
        severity="warning",
        pattern=re.compile(r"\.get\s*\(\s*[a-zA-Z_]\w*\.size\s*\(\s*\)\s*-\s*1\s*\)"),
        message="Manual last-element indexing via list.get(list.size() - 1) on Java 21+.",
        modern_replacement="Use SequencedCollection.getLast() (and getFirst() instead of .get(0)).",
    ),
    # --- Spring Boot 3.x+ Rules ---
    Rule(
        rule_id="BOOT-001",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="error",
        pattern=re.compile(r"^\s*import\s+javax\.(persistence|validation|servlet|annotation|transaction)\."),
        message="Legacy javax.* EE import detected in a Spring Boot 3.x+ project.",
        modern_replacement="Replace javax.* with jakarta.* (Jakarta EE 10).",
    ),
    Rule(
        rule_id="BOOT-002",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="error",
        pattern=re.compile(r"\bextends\s+WebSecurityConfigurerAdapter\b"),
        message="WebSecurityConfigurerAdapter was removed in Spring Security 6 / Spring Boot 3.",
        modern_replacement="Declare a @Bean SecurityFilterChain method using HttpSecurity Lambda DSL.",
    ),
    Rule(
        rule_id="BOOT-003",
        min_java=17,
        min_boot=(3, 2, 0),
        severity="warning",
        pattern=re.compile(r"\b(?:new\s+RestTemplate\s*\(|RestTemplateBuilder|RestTemplate)\b"),
        message="Legacy RestTemplate detected in Spring Boot 3.2+.",
        modern_replacement="Use RestClient (RestClient.builder()) or declarative @HttpExchange interfaces.",
    ),
    Rule(
        rule_id="BOOT-004",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="warning",
        pattern=re.compile(r"^\s*@Autowired\s*$"),
        message="Field injection with @Autowired makes testing harder and hides dependencies.",
        modern_replacement="Use constructor injection (final fields; omit @Autowired on single constructors).",
    ),
    Rule(
        rule_id="BOOT-005",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="error",
        pattern=re.compile(r"\.(?:antMatchers|mvcMatchers|authorizeRequests)\s*\("),
        message="Removed Spring Security 5 matcher/authorization API detected in Boot 3+.",
        modern_replacement="Use authorizeHttpRequests(auth -> auth.requestMatchers(...)).",
    ),
    Rule(
        rule_id="BOOT-006",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="error",
        pattern=re.compile(r"\.csrf\s*\(\s*\)\s*\.\s*disable\s*\(\s*\)"),
        message="Deprecated non-lambda .csrf().disable() syntax removed/deprecated in Spring Security 6.",
        modern_replacement="Use .csrf(AbstractHttpConfigurer::disable) or .csrf(csrf -> csrf.disable()).",
    ),
)


def _strip_line_comment(line: str, in_block_comment: bool) -> tuple[str, bool]:
    """Strip /* ... */ and // comments from a Java line while tracking block comment state."""
    out: list[str] = []
    i = 0
    n = len(line)
    in_str = False
    while i < n:
        if in_block_comment:
            if line[i : i + 2] == "*/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        ch = line[i]
        if ch == '"' and (i == 0 or line[i - 1] != "\\"):
            in_str = not in_str
            out.append(ch)
            i += 1
        elif not in_str and line[i : i + 2] == "//":
            break
        elif not in_str and line[i : i + 2] == "/*":
            in_block_comment = True
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out), in_block_comment


def scan_file(java_path: Path, profile: ProjectProfile) -> list[Finding]:
    """Scan a single .java file against rules applicable to the detected ProjectProfile."""
    findings: list[Finding] = []
    lines = java_path.read_text(encoding="utf-8", errors="replace").splitlines()
    in_block = False

    java_ver = profile.effective_java
    boot_ver = profile.effective_boot

    for idx, raw_line in enumerate(lines, start=1):
        code_line, in_block = _strip_line_comment(raw_line, in_block)
        if not code_line.strip():
            continue

        for rule in RULES:
            if java_ver < rule.min_java:
                continue
            if rule.min_boot is not None:
                if boot_ver is None or boot_ver < rule.min_boot:
                    continue

            if rule.pattern.search(code_line):
                findings.append(
                    Finding(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        file=str(java_path),
                        line=idx,
                        legacy_snippet=raw_line.strip(),
                        message=rule.message,
                        modern_replacement=rule.modern_replacement,
                    )
                )
    return findings


def scan_target(target: Path, profile: ProjectProfile) -> list[Finding]:
    """Scan a .java file or recursively scan all .java files under a directory."""
    if target.is_file():
        return scan_file(target, profile) if target.suffix == ".java" else []

    results: list[Finding] = []
    for java_file in sorted(target.rglob("*.java")):
        if any(part in {"target", "build", ".gradle", ".git"} for part in java_file.parts):
            continue
        results.extend(scan_file(java_file, profile))
    return results
