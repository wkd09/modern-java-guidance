<div align="center">

<img src="./assets/logo.svg" width="88" height="88" alt="modern-java-guidance logo" />

# Modern Java Guidance (`mjg`)

**Modern Java Guidance** is an Agent Skill, version detector, and `PostToolUse` hook that embeds **Java 17/21/25+** and **Spring Boot 3.x+** best practices directly into your AI coding agents.

[![CI](https://github.com/wkd09/modern-java-guidance/actions/workflows/ci.yml/badge.svg)](https://github.com/wkd09/modern-java-guidance/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](./pyproject.toml)
[![Dependencies: Zero](https://img.shields.io/badge/dependencies-zero-success.svg)](./pyproject.toml)

[English](./README.md) | [한국어](./README.ko.md) | [简体中文](./README.zh-CN.md)

</div>

---

## Why Modern Java Guidance?

Coding agents often default to **Java 8 and Spring Boot 2.x** patterns because LLM training datasets contain vast amounts of legacy enterprise code. Even inside a brand-new Java 21 + Spring Boot 3.x project, unguided models routinely emit removed `javax.*` imports, `WebSecurityConfigurerAdapter`, `RestTemplate`, or `Executors.newFixedThreadPool()`.

Even when a model knows a modern API exists, passive markdown skills alone cannot stop regressions mid-session. Modern Java Guidance bridges this gap with an executable CLI and `PostToolUse` guardrail:

* **Version-Aware Standard & Boot Detection (`mjg detect`)**: Parses `pom.xml`, `build.gradle(.kts)`, `gradle/libs.versions.toml`, and `.java-version` so legacy Java 8 / Boot 2.x repos never receive false-positive warnings.
* **On-Demand Knowledge Lookup (`mjg search` / `mjg retrieve`)**: Keeps `SKILL.md` at just **4.1 KB** while letting agents fetch exact Before/After patterns on demand.
* **Deterministic Post-Edit Guardrail (`mjg hook`)**: Automatically scans every edited `.java` file in **~31 ms** (zero LLM tokens) and blocks or warns on legacy regressions.

---

## Quickstart

Install `mjg` in one command (requires Python 3.11+, zero third-party dependencies):

```bash
curl -fsSL https://raw.githubusercontent.com/wkd09/modern-java-guidance/main/install.sh | bash
```

Then configure your Java/Spring Boot project (installs the skill + `PostToolUse` hooks):

```bash
mjg setup --target all --dir /path/to/your/spring-boot-project
```

### Try it out (without installing)

You can scan a project or search/retrieve guides directly via `uvx`:

```bash
# Scan a project respecting its pom.xml / build.gradle(.kts) versions
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg check .

# Search for relevant guides
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg search "security"

# Retrieve a specific guide by ID
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg retrieve BOOT-002
```

---

## Integration with Coding Agents & Tools

Modern Java Guidance integrates across major AI coding workflows:

* **Vercel's Agent Skills (Claude Code, Cursor, Copilot, Codex, Antigravity)**:
  ```bash
  npx skills add wkd09/modern-java-guidance
  ```
* **Antigravity (`PostToolUse` hook + global skill)**:
  ```bash
  mjg setup --target antigravity --dir .
  ```
* **Claude Code (`PostToolUse` hook returning `"decision": "block"`)**:
  ```bash
  mjg setup --target claude --dir .
  ```

<details>
<summary>Generated Hook Configuration (<code>.claude/settings.json</code> / <code>.agents/hooks.json</code>)</summary>

**Claude Code (`.claude/settings.json`)**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [{ "type": "command", "command": "mjg hook --format claude" }]
      }
    ]
  }
}
```

**Antigravity (`.agents/hooks.json`)**
```json
{
  "modern-java-guidance": {
    "PostToolUse": [
      {
        "matcher": "write_to_file|replace_file_content|multi_replace_file_content",
        "hooks": [{ "type": "command", "command": "mjg hook --format antigravity", "timeout": 10 }]
      }
    ]
  }
}
```

</details>

---

## What's Included?

* **Java 17 / 21 / 25+ Language & Stdlib**: `record`, `sealed interface`, Pattern Matching for `switch`, `SequencedCollection` (`getFirst()`, `getLast()`), Virtual Threads (`Executors.newVirtualThreadPerTaskExecutor()`), `java.time` (`Instant`, `DateTimeFormatter`), immutable collection factories (`List.of`, `Map.of`), and `String.formatted()`.
* **Spring Boot 3.x+ & Spring Security 6**: `jakarta.*` (Jakarta EE 10) migration, `SecurityFilterChain` Lambda DSL (`authorizeHttpRequests`, `requestMatchers`, `AbstractHttpConfigurer::disable`), `RestClient` & `@HttpExchange` (Boot 3.2+), constructor injection, and RFC 9457 `ProblemDetail`.
* **Legacy Preservation**: Automatically skips Java 21 and Boot 3+ rules when `pom.xml` or `build.gradle(.kts)` targets Java 8/11 or Spring Boot 2.x.

<details>
<summary>Full Version-Gated Rule Catalog (11 active scanner rules + 13 on-demand guides)</summary>

| Rule ID | Severity | Version Gate | Legacy Pattern | Modern Replacement |
| :--- | :--- | :--- | :--- | :--- |
| `JAVA-001` | `warning` | Java 16+ | `new Date()`, `SimpleDateFormat` | `java.time` (`Instant`, `LocalDate`, `DateTimeFormatter`) |
| `JAVA-002` | `warning` | Java 16+ | `Collections.unmodifiableList(Arrays.asList(...))` | `List.of(...)`, `Set.of(...)`, `Map.of(...)` |
| `JAVA-003` | `info` | Java 16+ | `String.format(...)` | `"..." .formatted(...)` |
| `JAVA-010` | `warning` | Java 21+ | `Executors.newFixedThreadPool` / `newCachedThreadPool` | `Executors.newVirtualThreadPerTaskExecutor()` (I/O-bound) |
| `JAVA-011` | `warning` | Java 21+ | `list.get(list.size() - 1)` | `SequencedCollection.getLast()` |
| `BOOT-001` | `error` | Boot 3.0+ | `import javax.{persistence,validation,servlet,...}.*` | `import jakarta.*` |
| `BOOT-002` | `error` | Boot 3.0+ | `extends WebSecurityConfigurerAdapter` | `@Bean SecurityFilterChain` |
| `BOOT-003` | `warning` | Boot 3.2+ | `RestTemplate` / `RestTemplateBuilder` | `RestClient` / `@HttpExchange` |
| `BOOT-004` | `warning` | Boot 3.0+ | `@Autowired` field injection | Constructor injection |
| `BOOT-005` | `error` | Boot 3.0+ | `.antMatchers()` / `.mvcMatchers()` / `.authorizeRequests()` | `.authorizeHttpRequests(a -> a.requestMatchers(...))` |
| `BOOT-006` | `error` | Boot 3.0+ | `.csrf().disable()` | `.csrf(AbstractHttpConfigurer::disable)` |

</details>

---

## Evaluation & Benchmarks

### 1. Assertion-Based A/B Evaluation (`scripts/eval_suite.py`)

Modeled after `GoogleChrome/modern-web-guidance`'s assertion grading approach, `scripts/eval_suite.py` evaluates **6 representative Java / Spring Boot tasks** under two conditions—**Unguided Legacy Baseline** vs. **Guided + `mjg` Hook**—verifying required modern patterns, forbidden legacy patterns, and zero `mjg` violations:

| Metric | Unguided Legacy Baseline | Guided + `mjg` Hook | Uplift |
| :--- | :--- | :--- | :--- |
| **Overall Task Pass Rate** | **1 / 6 (16.7%)** | **6 / 6 (100.0%)** | **+83.3 pp** |

| Task | Target | Unguided Baseline | Guided + `mjg` Hook |
| :--- | :--- | :--- | :--- |
| `EVAL-01` Spring Security 6 Config | Java 21, Boot 3.3.4 | FAIL (3 `mjg` findings) | **PASS** (0 findings) |
| `EVAL-02` Synchronous HTTP Client | Java 21, Boot 3.3.4 | FAIL (3 `mjg` findings) | **PASS** (0 findings) |
| `EVAL-03` Jakarta EE Persistence/Validation | Java 21, Boot 3.3.4 | FAIL (2 `mjg` findings) | **PASS** (0 findings) |
| `EVAL-04` Blocking I/O Concurrency | Java 21, Boot 3.3.4 | FAIL (1 `mjg` finding) | **PASS** (0 findings) |
| `EVAL-05` SequencedCollection & `java.time` | Java 21, Boot 3.3.4 | FAIL (2 `mjg` findings) | **PASS** (0 findings) |
| `EVAL-06` Legacy Compatibility Preservation | Java 8, Boot 2.7.18 | PASS (0 false positives) | **PASS** (0 false positives) |

### 2. Comparison with Existing Java & Spring Boot Skills

| Feature / Metric | **`modern-java-guidance` (`mjg`)** | **`github/awesome-copilot`**<br>(`java-springboot` + `spring-security`) | **`Amplicode/spring-skills`**<br>(`spring-security-configuration`) | **`Santoshrt999/Java-Claude-Skills`**<br>(`java-modernization-review`) |
| :--- | :--- | :--- | :--- | :--- |
| **Initial `SKILL.md` Size** | **4,157 bytes** | 9,737 bytes (4,433 + 5,304) | 17,344 bytes (4.2×) | 20,103 bytes (4.8×) |
| **Executable CLI Scanner** | ✅ `mjg check` (0 LLM tokens) | ❌ Markdown only | ❌ None | ❌ Markdown only |
| **Auto Version Detection** | ✅ `mjg detect` (`pom.xml` / Gradle) | ⚠️ Manual agent read | ⚠️ Requires IntelliJ MCP | ❌ None |
| **`PostToolUse` Auto-Block Hook** | ✅ Antigravity & Claude Code | ❌ None | ❌ None | ❌ None |
| **External / IDE Dependencies** | **Zero** (Python stdlib only) | None | ❌ IntelliJ Amplicode MCP | None |

### 3. Throughput & Latency (`scripts/benchmark.py`)

Measured on Apple Silicon (Python standard library only):

| Benchmark | Workload | Result |
| :--- | :--- | :--- |
| **Repo scan** (`detect` + `scan_target`) | 10 / 100 / 500 / 1,000 Java files | **3.10 ms** / **22.84 ms** / **105.24 ms** / **183.40 ms** (`0.183 ms/file`) |
| **Build file detection** | `pom.xml` / `build.gradle.kts` / `.java-version` | **0.059 ms** / **0.043 ms** / **0.045 ms** |
| **`PostToolUse` hook (in-process)** | Single `.java` file (50 runs) | **p50 0.257 ms** · p95 0.317 ms · max 0.373 ms |
| **CLI subprocess E2E (`mjg hook`)** | Full process spawn (10 runs) | **31.0 ms median** (30.5–86.3 ms) |

---

## License

[MIT](./LICENSE)
