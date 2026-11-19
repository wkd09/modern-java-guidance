"""Export version-gated modern-java-guidance rules to external static analyzers (Semgrep)."""

from __future__ import annotations

from dataclasses import dataclass

from modern_java_guidance.detector import ProjectProfile


@dataclass(slots=True, frozen=True)
class SemgrepRuleSpec:
    rule_id: str
    semgrep_id: str
    min_java: int
    min_boot: tuple[int, int, int] | None
    severity: str  # ERROR, WARNING, INFO
    caught_by_javac: str
    message: str
    pattern_yaml: str


SEMGREP_RULES: tuple[SemgrepRuleSpec, ...] = (
    SemgrepRuleSpec(
        rule_id="JAVA-001",
        semgrep_id="mjg-java-001-legacy-date-api",
        min_java=16,
        min_boot=None,
        severity="WARNING",
        caught_by_javac="no",
        message="Legacy mutable date/time API detected. Use java.time (Instant.now(), LocalDate, DateTimeFormatter).",
        pattern_yaml="""    pattern-either:
      - pattern: new Date()
      - pattern: new java.util.Date()
      - pattern: new SimpleDateFormat(...)""",
    ),
    SemgrepRuleSpec(
        rule_id="JAVA-002",
        semgrep_id="mjg-java-002-unmodifiable-aslist",
        min_java=16,
        min_boot=None,
        severity="WARNING",
        caught_by_javac="no",
        message="Verbose pre-Java 9 unmodifiable collection boilerplate. Use List.of(...), Set.of(...), or Map.of(...).",
        pattern_yaml="""    pattern-either:
      - pattern: Collections.unmodifiableList(Arrays.asList(...))
      - pattern: Collections.unmodifiableSet(Arrays.asList(...))""",
    ),
    SemgrepRuleSpec(
        rule_id="JAVA-003",
        semgrep_id="mjg-java-003-string-format",
        min_java=16,
        min_boot=None,
        severity="INFO",
        caught_by_javac="no",
        message="Prefer Java 15+ \"...\".formatted(args...) over static String.format(...) when no explicit Locale is needed.",
        pattern_yaml="""    patterns:
      - pattern: String.format($FMT, ...)
      - pattern-not: String.format((java.util.Locale $LOC), ...)
      - pattern-not: String.format(Locale.$LOC, ...)""",
    ),
    SemgrepRuleSpec(
        rule_id="JAVA-010",
        semgrep_id="mjg-java-010-platform-thread-pool",
        min_java=21,
        min_boot=None,
        severity="WARNING",
        caught_by_javac="no",
        message="Platform thread pool used on Java 21+. Prefer Executors.newVirtualThreadPerTaskExecutor() for blocking I/O workloads (keep bounded pools for CPU-bound or rate-limited tasks).",
        pattern_yaml="""    pattern-either:
      - pattern: Executors.newFixedThreadPool(...)
      - pattern: Executors.newCachedThreadPool()""",
    ),
    SemgrepRuleSpec(
        rule_id="JAVA-011",
        semgrep_id="mjg-java-011-sequenced-get-last",
        min_java=21,
        min_boot=None,
        severity="WARNING",
        caught_by_javac="no",
        message="Manual last-element indexing on Java 21+. Use SequencedCollection.getLast().",
        pattern_yaml="""    pattern: $LIST.get($LIST.size() - 1)""",
    ),
    SemgrepRuleSpec(
        rule_id="BOOT-001",
        semgrep_id="mjg-boot-001-javax-ee-import",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="ERROR",
        caught_by_javac="compile-error",
        message="Legacy javax.* EE import in Spring Boot 3.x+. Replace with jakarta.* (Jakarta EE 10).",
        pattern_yaml="""    pattern-regex: '^\\s*import\\s+javax\\.(persistence|validation|servlet|annotation|transaction)\\.'""",
    ),
    SemgrepRuleSpec(
        rule_id="BOOT-002",
        semgrep_id="mjg-boot-002-websecurityconfigureradapter",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="ERROR",
        caught_by_javac="compile-error",
        message="WebSecurityConfigurerAdapter was removed in Spring Security 6 / Spring Boot 3. Declare a @Bean SecurityFilterChain method using HttpSecurity Lambda DSL.",
        pattern_yaml="""    pattern: |
      class $CLS extends WebSecurityConfigurerAdapter {
        ...
      }""",
    ),
    SemgrepRuleSpec(
        rule_id="BOOT-003",
        semgrep_id="mjg-boot-003-resttemplate",
        min_java=17,
        min_boot=(3, 2, 0),
        severity="WARNING",
        caught_by_javac="no",
        message="Legacy RestTemplate used in Spring Boot 3.2+. Prefer RestClient (RestClient.builder()) or declarative @HttpExchange interfaces.",
        pattern_yaml="""    pattern-either:
      - pattern: new RestTemplate(...)
      - pattern: RestTemplate $VAR;
      - pattern: RestTemplate $VAR = ...;
      - pattern: RestTemplateBuilder $VAR;
      - pattern: $RET $METHOD(..., RestTemplateBuilder $VAR, ...) { ... }
      - pattern: $RET $METHOD(..., RestTemplate $VAR, ...) { ... }""",
    ),
    SemgrepRuleSpec(
        rule_id="BOOT-004",
        semgrep_id="mjg-boot-004-autowired-field-injection",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="WARNING",
        caught_by_javac="no",
        message="Field injection with @Autowired hides dependencies and complicates unit testing. Prefer constructor injection with private final fields.",
        pattern_yaml="""    pattern: |
      @Autowired
      $TYPE $FIELD;""",
    ),
    SemgrepRuleSpec(
        rule_id="BOOT-005",
        semgrep_id="mjg-boot-005-security-legacy-matchers",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="ERROR",
        caught_by_javac="compile-error",
        message="Removed Spring Security 5 matcher/authorization API. Use authorizeHttpRequests(auth -> auth.requestMatchers(...)).",
        pattern_yaml="""    pattern-either:
      - pattern: $HTTP.antMatchers(...)
      - pattern: $HTTP.mvcMatchers(...)
      - pattern: $HTTP.authorizeRequests(...)""",
    ),
    SemgrepRuleSpec(
        rule_id="BOOT-006",
        semgrep_id="mjg-boot-006-csrf-chained-disable",
        min_java=17,
        min_boot=(3, 0, 0),
        severity="ERROR",
        caught_by_javac="deprecated",
        message="Deprecated non-lambda .csrf().disable() syntax. Keep CSRF enabled by default; only use .csrf(AbstractHttpConfigurer::disable) for non-browser-attached credentials (e.g., Bearer JWT).",
        pattern_yaml="""    pattern: $HTTP.csrf().disable()""",
    ),
)


def _yaml_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def filter_semgrep_rules(profile: ProjectProfile) -> list[SemgrepRuleSpec]:
    java_ver = profile.effective_java
    boot_ver = profile.effective_boot
    selected: list[SemgrepRuleSpec] = []
    for spec in SEMGREP_RULES:
        if java_ver < spec.min_java:
            continue
        if spec.min_boot is not None:
            if boot_ver is None or boot_ver < spec.min_boot:
                continue
        selected.append(spec)
    return selected


def export_semgrep_yaml(profile: ProjectProfile) -> str:
    """Generate a valid Semgrep YAML ruleset filtered for the given ProjectProfile."""
    selected = filter_semgrep_rules(profile)
    boot_str = ".".join(map(str, profile.effective_boot)) if profile.effective_boot else "none"
    lines: list[str] = [
        f"# Generated by modern-java-guidance (mjg) for Java {profile.effective_java}, Spring Boot {boot_str}",
        "# Run with: semgrep --config <this-file.yaml> .",
    ]
    if not selected:
        lines.append("rules: []")
        return "\n".join(lines) + "\n"

    lines.append("rules:")
    for spec in selected:
        min_boot_label = ".".join(map(str, spec.min_boot)) if spec.min_boot else "none"
        lines.append(f"  - id: {spec.semgrep_id}")
        lines.append("    languages: [java]")
        lines.append(f"    severity: {spec.severity}")
        lines.append(f'    message: "{_yaml_escape(spec.message)}"')
        lines.append("    metadata:")
        lines.append(f'      mjg_rule_id: "{spec.rule_id}"')
        lines.append(f"      min_java: {spec.min_java}")
        lines.append(f'      min_boot: "{min_boot_label}"')
        lines.append(f'      caught_by_javac: "{spec.caught_by_javac}"')
        lines.append("      category: best-practice")
        lines.append(spec.pattern_yaml)
    return "\n".join(lines) + "\n"
