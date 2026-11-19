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
    caught_by_javac: str
    file: str
    line: int
    legacy_snippet: str
    message: str
    modern_replacement: str

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "caught_by_javac": self.caught_by_javac,
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
    caught_by_javac: str
    pattern: re.Pattern[str]
    message: str
    modern_replacement: str
    multiline: bool = False
    skip_imports: bool = False


RULES: tuple[Rule, ...] = (
    # --- Java 17+ Rules ---
    Rule(
        rule_id="JAVA-001",
        min_java=16,
        min_boot=None,
        severity="warning",
        caught_by_javac="no",
        pattern=re.compile(
            r"\bnew\s+(?:java\.util\.)?Date\s*\(\s*\)|new\s+SimpleDateFormat\s*\(|\bCalendar\.getInstance\s*\("
        ),
        message="Legacy mutable date/time API detected.",
        modern_replacement="Use java.time (Instant.now(), LocalDate, ZonedDateTime, DateTimeFormatter).",
    ),
    Rule(
        rule_id="JAVA-002",
        min_java=16,
        min_boot=None,
        severity="warning",
        caught_by_javac="no",
        pattern=re.compile(r"Collections\.unmodifiable(?:List|Set|Map)\s*\(\s*Arrays\.asList\s*\("),
        message="Verbose pre-Java 9 unmodifiable collection boilerplate.",
        modern_replacement="Use List.of(...), Set.of(...), or Map.of(...).",
    ),
    Rule(
        rule_id="JAVA-003",
        min_java=16,
        min_boot=None,
        severity="info",
        caught_by_javac="no",
        pattern=re.compile(r"\bString\.format\s*\(\s*(?!(?:java\.util\.)?Locale\b|locale\b)"),
        message="Static String.format(...) can be written more readably with Java 15+ .formatted(...).",
        modern_replacement='Use "...".formatted(args...) (keep String.format(Locale, ...) when an explicit Locale is needed).',
    ),
    Rule(
        rule_id="JAVA-004",
        min_java=16,
        min_boot=None,
        severity="info",
        caught_by_javac="no",
        pattern=re.compile(r"\.collect\s*\(\s*Collectors\.toList\s*\(\s*\)\s*\)"),
        message="Verbose Collectors.toList() on Java 16+.",
        modern_replacement="Use Stream.toList() (or Collectors.toCollection(ArrayList::new) if a mutable list is required).",
    ),
    # --- Java 21+ Rules ---
    Rule(
        rule_id="JAVA-010",
        min_java=21,
        min_boot=None,
        severity="warning",
        caught_by_javac="no",
        pattern=re.compile(r"Executors\.new(?:FixedThreadPool|CachedThreadPool)\s*\("),
        message="Platform thread pool used on Java 21+ for potentially I/O-bound concurrency.",
        modern_replacement="Prefer Executors.newVirtualThreadPerTaskExecutor() for I/O-bound workloads (keep bounded pools/semaphores only for CPU-bound or rate-limited tasks).",
    ),
    Rule(
        rule_id="JAVA-011",
        min_java=21,
        min_boot=None,
        severity="warning",
        caught_by_javac="no",
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
        caught_by_javac="compile-error",
        pattern=re.compile(
            r"^\s*import\s+javax\.(persistence|validation|servlet|annotation|transaction|inject|mail|xml\.bind|ws\.rs)\."
        ),
        message="Legacy javax.* EE import detected in a Spring Boot 3.x+ project.",
        modern_replacement="Replace javax.* with jakarta.* (Jakarta EE 10).",
    ),
    Rule(
        rule_id="BOOT-002",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="error",
        caught_by_javac="compile-error",
        pattern=re.compile(r"\bextends\s+WebSecurityConfigurerAdapter\b"),
        message="WebSecurityConfigurerAdapter was removed in Spring Security 6 / Spring Boot 3.",
        modern_replacement="Declare a @Bean SecurityFilterChain method using HttpSecurity Lambda DSL.",
    ),
    Rule(
        rule_id="BOOT-003",
        min_java=17,
        min_boot=(3, 2, 0),
        severity="warning",
        caught_by_javac="no",
        pattern=re.compile(r"\b(?:new\s+RestTemplate\s*\(|RestTemplateBuilder|RestTemplate)\b"),
        message="Legacy RestTemplate detected in Spring Boot 3.2+.",
        modern_replacement="Use RestClient (RestClient.builder()) or declarative @HttpExchange interfaces.",
        skip_imports=True,
    ),
    Rule(
        rule_id="BOOT-004",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="warning",
        caught_by_javac="no",
        # Handled with lookahead field detection in _scan_autowired_field_injection()
        pattern=re.compile(r"(?!x)x"),
        message="Field injection with @Autowired makes testing harder and hides dependencies.",
        modern_replacement="Use constructor injection (final fields; omit @Autowired on single constructors).",
    ),
    Rule(
        rule_id="BOOT-005",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="error",
        caught_by_javac="compile-error",
        pattern=re.compile(r"\.(?:antMatchers|mvcMatchers|authorizeRequests)\s*\("),
        message="Removed Spring Security 5 matcher/authorization API detected in Boot 3+.",
        modern_replacement="Use authorizeHttpRequests(auth -> auth.requestMatchers(...)).",
    ),
    Rule(
        rule_id="BOOT-006",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="error",
        caught_by_javac="deprecated",
        pattern=re.compile(r"\.csrf\s*\(\s*\)\s*\.\s*disable\s*\(\s*\)"),
        message="Deprecated non-lambda .csrf().disable() syntax removed/deprecated in Spring Security 6.",
        modern_replacement="Keep CSRF enabled by default; only use .csrf(AbstractHttpConfigurer::disable) for non-browser-attached credentials (e.g., Bearer JWT).",
        multiline=True,
    ),
    Rule(
        rule_id="BOOT-008",
        min_java=17,
        min_boot=(3, 4, 0),
        severity="warning",
        caught_by_javac="deprecated",
        pattern=re.compile(
            r"org\.springframework\.boot\.test\.mock\.mockito\.(?:MockBean|SpyBean)|@(?:MockBean|SpyBean)\b"
        ),
        message="@MockBean / @SpyBean are deprecated in Spring Boot 3.4+.",
        modern_replacement="Use @MockitoBean / @MockitoSpyBean (org.springframework.test.context.bean.override.mockito.*).",
    ),
)

_IGNORE_RE = re.compile(r"mjg:ignore(?:\s+([A-Za-z0-9_,\-\s]+))?", re.IGNORECASE)
_RULE_ID_TOKEN_RE = re.compile(r"[A-Za-z]+-\d+")
_AUTOWIRED_RE = re.compile(r"@Autowired(?:\s*\([^)]*\))?")
_IMPORT_LINE_RE = re.compile(r"^\s*import\s+")


def _parse_ignore_comment(comment_text: str) -> set[str] | None:
    m = _IGNORE_RE.search(comment_text)
    if not m:
        return None
    raw_ids = m.group(1)
    if not raw_ids or not raw_ids.strip():
        return {"*"}
    tokens = {tok.upper() for tok in _RULE_ID_TOKEN_RE.findall(raw_ids)}
    return tokens if tokens else {"*"}


def _sanitize_java_lines(lines: list[str]) -> tuple[list[str], dict[int, set[str]]]:
    """Strip Java comments, string literals, char literals, and text blocks while preserving line count.

    Also extracts inline and preceding-line `// mjg:ignore [RULE-ID ...]` directives.
    """
    sanitized: list[str] = []
    ignores: dict[int, set[str]] = {}
    in_block_comment = False
    in_text_block = False

    for line_no, line in enumerate(lines, start=1):
        out: list[str] = []
        comment_chunks: list[str] = []
        i = 0
        n = len(line)
        in_str = False
        in_char = False

        while i < n:
            if in_block_comment:
                if line[i : i + 2] == "*/":
                    in_block_comment = False
                    i += 2
                else:
                    comment_chunks.append(line[i])
                    i += 1
                continue

            if in_text_block:
                if line[i] == "\\":
                    i += 2
                elif line[i : i + 3] == '"""':
                    in_text_block = False
                    out.append('""')
                    i += 3
                else:
                    i += 1
                continue

            if in_str:
                if line[i] == "\\":
                    i += 2
                elif line[i] == '"':
                    in_str = False
                    out.append('"')
                    i += 1
                else:
                    i += 1
                continue

            if in_char:
                if line[i] == "\\":
                    i += 2
                elif line[i] == "'":
                    in_char = False
                    out.append("'")
                    i += 1
                else:
                    i += 1
                continue

            if line[i : i + 2] == "//":
                comment_chunks.append(line[i + 2 :])
                break
            if line[i : i + 2] == "/*":
                in_block_comment = True
                i += 2
                continue
            if line[i : i + 3] == '"""':
                in_text_block = True
                out.append('""')
                i += 3
                continue
            if line[i] == '"':
                in_str = True
                out.append('"')
                i += 1
                continue
            if line[i] == "'":
                in_char = True
                out.append("'")
                i += 1
                continue

            out.append(line[i])
            i += 1

        code_line = "".join(out)
        sanitized.append(code_line)

        if comment_chunks:
            parsed = _parse_ignore_comment(" ".join(comment_chunks))
            if parsed:
                ignores.setdefault(line_no, set()).update(parsed)
                # If this line has no code, apply ignore directive to the next line as well
                if not code_line.strip():
                    ignores.setdefault(line_no + 1, set()).update(parsed)

    return sanitized, ignores


def _is_ignored(ignores: dict[int, set[str]], line_no: int, rule_id: str) -> bool:
    line_ignores = ignores.get(line_no)
    if not line_ignores:
        return False
    return "*" in line_ignores or rule_id.upper() in line_ignores


def _is_test_java_file(java_path: Path) -> bool:
    parts_lower = [p.lower() for p in java_path.parts]
    for i in range(len(parts_lower) - 1):
        if parts_lower[i] == "src" and parts_lower[i + 1] == "test":
            return True
    stem = java_path.stem
    return stem.endswith(("Test", "Tests", "IT"))


def _looks_like_field_decl(stmt: str) -> bool:
    """Return True if a Java member declaration line looks like a field (not a constructor/method)."""
    stripped = stmt.strip()
    if not stripped or stripped.startswith("@"):
        return False
    # Constructors/methods have '(' before ';' or '=' (or have no ';'/'=' and contain '(')
    paren_idx = stripped.find("(")
    semi_idx = stripped.find(";")
    eq_idx = stripped.find("=")
    term_candidates = [idx for idx in (semi_idx, eq_idx) if idx != -1]
    if paren_idx != -1:
        if not term_candidates or paren_idx < min(term_candidates):
            return False
    # Must look like a type + field name (at least 2 tokens, not closing brace or class header)
    if re.search(r"\b(?:class|interface|record|enum)\b", stripped):
        return False
    return bool(re.search(r"[A-Za-z_][\w<>\[\], ?]*\s+[A-Za-z_]\w*\s*(?:=|;|$)", stripped))


def _scan_autowired_field_injection(
    java_path: Path,
    raw_lines: list[str],
    code_lines: list[str],
    ignores: dict[int, set[str]],
    rule: Rule,
) -> list[Finding]:
    if _is_test_java_file(java_path):
        return []

    findings: list[Finding] = []
    n = len(code_lines)
    for idx in range(n):
        line_no = idx + 1
        code_line = code_lines[idx]
        m = _AUTOWIRED_RE.search(code_line)
        if not m:
            continue
        if _is_ignored(ignores, line_no, rule.rule_id):
            continue

        remainder = code_line[m.end() :].strip()
        is_field = False
        if remainder:
            # Inline form: `@Autowired private UserRepository repo;` or `@Autowired public Foo(Bar b)`
            is_field = _looks_like_field_decl(remainder)
        else:
            # Multi-line form: scan ahead past blank lines and sibling annotations
            j = idx + 1
            while j < n:
                nxt = code_lines[j].strip()
                if not nxt or nxt.startswith("@"):
                    j += 1
                    continue
                is_field = _looks_like_field_decl(nxt)
                break

        if is_field:
            findings.append(
                Finding(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    caught_by_javac=rule.caught_by_javac,
                    file=str(java_path),
                    line=line_no,
                    legacy_snippet=raw_lines[idx].strip(),
                    message=rule.message,
                    modern_replacement=rule.modern_replacement,
                )
            )
    return findings


def _rule_enabled(rule_min_java: int, rule_min_boot: tuple[int, int, int] | None, profile: ProjectProfile) -> bool:
    if profile.effective_java < rule_min_java:
        return False
    if rule_min_boot is not None:
        if profile.effective_boot is None or profile.effective_boot < rule_min_boot:
            return False
    return True


def scan_file(java_path: Path, profile: ProjectProfile) -> list[Finding]:
    """Scan a single .java file against rules applicable to the detected ProjectProfile."""
    findings: list[Finding] = []
    raw_lines = java_path.read_text(encoding="utf-8", errors="replace").splitlines()
    code_lines, ignores = _sanitize_java_lines(raw_lines)

    active_line_rules: list[Rule] = []
    active_multiline_rules: list[Rule] = []
    autowired_rule: Rule | None = None

    for rule in RULES:
        if not _rule_enabled(rule.min_java, rule.min_boot, profile):
            continue
        if rule.rule_id == "BOOT-004":
            autowired_rule = rule
        elif rule.multiline:
            active_multiline_rules.append(rule)
        else:
            active_line_rules.append(rule)

    # 1. Line-by-line rules
    for idx, code_line in enumerate(code_lines, start=1):
        if not code_line.strip():
            continue
        is_import = bool(_IMPORT_LINE_RE.match(code_line))
        for rule in active_line_rules:
            if rule.skip_imports and is_import:
                continue
            if _is_ignored(ignores, idx, rule.rule_id):
                continue
            if rule.pattern.search(code_line):
                findings.append(
                    Finding(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        caught_by_javac=rule.caught_by_javac,
                        file=str(java_path),
                        line=idx,
                        legacy_snippet=raw_lines[idx - 1].strip(),
                        message=rule.message,
                        modern_replacement=rule.modern_replacement,
                    )
                )

    # 2. Smart @Autowired field injection rule (BOOT-004)
    if autowired_rule is not None:
        findings.extend(_scan_autowired_field_injection(java_path, raw_lines, code_lines, ignores, autowired_rule))

    # 3. Multiline rules (e.g. BOOT-006 multiline .csrf()\n.disable())
    if active_multiline_rules:
        joined = "\n".join(code_lines)
        for rule in active_multiline_rules:
            for match in rule.pattern.finditer(joined):
                start_line = joined.count("\n", 0, match.start()) + 1
                end_line = joined.count("\n", 0, match.end()) + 1
                if _is_ignored(ignores, start_line, rule.rule_id) or _is_ignored(ignores, end_line, rule.rule_id):
                    continue
                snippet = " ".join(raw_lines[ln - 1].strip() for ln in range(start_line, end_line + 1))
                findings.append(
                    Finding(
                        rule_id=rule.rule_id,
                        severity=rule.severity,
                        caught_by_javac=rule.caught_by_javac,
                        file=str(java_path),
                        line=start_line,
                        legacy_snippet=snippet,
                        message=rule.message,
                        modern_replacement=rule.modern_replacement,
                    )
                )

    findings.sort(key=lambda f: (f.line, f.rule_id))
    return findings


def _is_build_config_file(path: Path) -> bool:
    return path.name in {"pom.xml", "build.gradle", "build.gradle.kts", "libs.versions.toml"}


def _is_dockerfile(path: Path) -> bool:
    name = path.name
    return name == "Dockerfile" or name.startswith("Dockerfile.") or name.endswith(".Dockerfile")


def scan_config_file(config_path: Path, profile: ProjectProfile) -> list[Finding]:
    """Scan Spring Boot build files and Dockerfiles for Boot 3.x observability/deployment issues."""
    findings: list[Finding] = []
    boot_ver = profile.effective_boot
    if boot_ver is None:
        return findings

    raw_lines = config_path.read_text(encoding="utf-8", errors="replace").splitlines()

    # BOOT-009: Spring Cloud Sleuth removed/incompatible in Spring Boot 3.0+
    if _is_build_config_file(config_path) and boot_ver >= (3, 0, 0):
        for idx, line in enumerate(raw_lines, start=1):
            if "mjg:ignore" in line and ("BOOT-009" in line.upper() or not _RULE_ID_TOKEN_RE.search(line)):
                continue
            if "spring-cloud-starter-sleuth" in line or "spring-cloud-sleuth" in line:
                findings.append(
                    Finding(
                        rule_id="BOOT-009",
                        severity="error",
                        caught_by_javac="no",
                        file=str(config_path),
                        line=idx,
                        legacy_snippet=line.strip(),
                        message="Spring Cloud Sleuth is not compatible with Spring Boot 3.x+.",
                        modern_replacement="Migrate to Micrometer Tracing + OpenTelemetry OTLP (micrometer-tracing-bridge-otel, opentelemetry-exporter-otlp).",
                    )
                )

    # BOOT-010: Naive fat-JAR `java -jar` in Dockerfile on Spring Boot 3.3+
    if _is_dockerfile(config_path) and boot_ver >= (3, 3, 0):
        full_text = "\n".join(raw_lines)
        has_modern_layout = any(
            marker in full_text
            for marker in ("-Djarmode=tools", "-Djarmode=layertools", "SharedArchiveFile", "extract")
        )
        if not has_modern_layout:
            fat_jar_re = re.compile(r"""^\s*(?:ENTRYPOINT|CMD)\b.*java.*[\s"']-jar\b.*\.jar""", re.IGNORECASE)
            for idx, line in enumerate(raw_lines, start=1):
                if line.lstrip().startswith("#"):
                    continue
                prev_ignore = idx > 1 and "mjg:ignore" in raw_lines[idx - 2]
                if prev_ignore or "mjg:ignore" in line:
                    continue
                if fat_jar_re.search(line):
                    findings.append(
                        Finding(
                            rule_id="BOOT-010",
                            severity="info",
                            caught_by_javac="no",
                            file=str(config_path),
                            line=idx,
                            legacy_snippet=line.strip(),
                            message="Running an unextracted fat JAR directly in a Spring Boot 3.3+ container slows image layers and startup.",
                            modern_replacement="Use `java -Djarmode=tools -jar app.jar extract` (extracted layout), Cloud Native Buildpacks (spring-boot:build-image), or AppCDS.",
                        )
                    )

    return findings


def scan_target(target: Path, profile: ProjectProfile) -> list[Finding]:
    """Scan a single file or recursively scan Java, build, and Dockerfile targets under a directory."""
    if target.is_file():
        if target.suffix == ".java":
            return scan_file(target, profile)
        if _is_build_config_file(target) or _is_dockerfile(target):
            return scan_config_file(target, profile)
        return []

    results: list[Finding] = []
    skip_dirs = {"target", "build", ".gradle", ".git"}

    for java_file in sorted(target.rglob("*.java")):
        if any(part in skip_dirs for part in java_file.parts):
            continue
        results.extend(scan_file(java_file, profile))

    if profile.effective_boot is not None:
        seen_configs: set[Path] = set()
        for pattern in ("pom.xml", "build.gradle", "build.gradle.kts", "libs.versions.toml", "Dockerfile", "Dockerfile.*", "*.Dockerfile"):
            for cfg in sorted(target.rglob(pattern)):
                if cfg in seen_configs or not cfg.is_file():
                    continue
                if any(part in skip_dirs for part in cfg.parts):
                    continue
                seen_configs.add(cfg)
                results.extend(scan_config_file(cfg, profile))

    return results
