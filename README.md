<div align="center">

<img src="./assets/logo.svg" width="88" height="88" alt="modern-java-guidance logo" />

# Modern Java Guidance

**Modern Java Guidance** is an Agent Skill, CLI scanner, and `PostToolUse` hook that embeds **Java 17/21/25+** and **Spring Boot 3.x+** best practices directly into your coding agents. It steers your coding agents away from Java 8 & Spring Boot 2.x legacy patterns, and toward modern, production-ready idioms.

[![CI](https://github.com/wkd09/modern-java-guidance/actions/workflows/ci.yml/badge.svg)](https://github.com/wkd09/modern-java-guidance/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](./pyproject.toml)
[![Dependencies: Zero](https://img.shields.io/badge/dependencies-zero-success.svg)](./pyproject.toml)

[English](./README.md) | [한국어](./README.ko.md) | [简体中文](./README.zh-CN.md)

[Skill Guide](./skills/modern-java-guidance/SKILL.md) · [Semgrep Rules](./rules/semgrep/modern-java-boot3.yaml) · [Eval Suite](./scripts/eval_suite.py) · [Benchmarks](./scripts/benchmark.py) · [Report an Issue](https://github.com/wkd09/modern-java-guidance/issues)

</div>

---

## Quickstart

```bash
curl -fsSL https://raw.githubusercontent.com/wkd09/modern-java-guidance/main/install.sh | bash
mjg setup --target all --dir /path/to/your/spring-boot-project
```

This installs `mjg` (zero third-party dependencies, Python 3.11+) and configures the Agent Skill + `PostToolUse` hooks. See [Alternative Installation Methods](#alternative-installation-methods) below.

### Try it out (without installing)

```bash
# Search for relevant guides
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg search "security"

# Retrieve a guide by ID
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg retrieve BOOT-002

# Scan a codebase for legacy Java / Spring Boot patterns
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg check .
```

---

## Why?

Coding agents often default to **Java 8 and Spring Boot 2.x** patterns because LLM training data contains vast amounts of legacy enterprise code. This frequently leads them to generate removed `javax.*` imports, `WebSecurityConfigurerAdapter`, `RestTemplate`, or blocking `Executors.newFixedThreadPool()` inside modern Java 21 + Spring Boot 3.x projects.

Even if a model knows a modern API exists, passive markdown skills alone cannot stop regressions mid-session. **Modern Java Guidance** bridges this gap with an offline CLI and `PostToolUse` guardrail, focusing on:

* **Modern Java & Spring Boot APIs**: Steering models toward `SecurityFilterChain` Lambda DSL, `RestClient`, `@HttpExchange`, `record`, `sealed interface`, `SequencedCollection`, and Virtual Threads.
* **Version-Aware Safety**: Detecting `pom.xml`, `build.gradle(.kts)`, `libs.versions.toml`, and `.java-version` so legacy Java 8 / Boot 2.x projects never receive false-positive warnings.
* **Deterministic Post-Edit Guardrails**: Scanning every edited `.java` file in **~31 ms** (zero LLM tokens) to catch and block legacy regressions before they land.

---

## What's Included?

We cover modern **Java 17 / 21 / 25+** and **Spring Boot 3.x+** patterns. The skill is designed to be token-efficient: `SKILL.md` is only **4.8 KB**, while detailed Before/After guides are fetched on demand via `mjg search` and `mjg retrieve`.

### Core Disciplines

* **🔒 Spring Security 6**: `SecurityFilterChain` `@Bean`, Lambda DSL, `authorizeHttpRequests()`, `requestMatchers()`, and `AbstractHttpConfigurer::disable`.
* **🌐 Modern HTTP Clients**: Fluent `RestClient` and declarative `@HttpExchange` interfaces (Spring Boot 3.2+) replacing `RestTemplate`.
* **⚡ Virtual Threads & Concurrency**: `Executors.newVirtualThreadPerTaskExecutor()` for blocking I/O workloads, with bounded-pool caveats for CPU-bound tasks.
* **🧩 Modern Java Language**: `record`, `sealed interface`, Pattern Matching for `switch`, `SequencedCollection` (`getFirst()`, `getLast()`), `java.time`, `List.of`/`Map.of`, and `String.formatted()`.
* **🏛️ Jakarta EE 10 & Clean DI**: `jakarta.*` migration (`persistence`, `validation`, `servlet`), constructor injection over `@Autowired` field injection, and RFC 9457 `ProblemDetail`.
* **🛡️ Legacy Preservation**: Automatically gates rules by detected `pom.xml` / `build.gradle(.kts)` versions so Java 8/11 and Boot 2.x repos stay untouched.

### The full list (17 guides, 15 active scanner rules & 13 Semgrep exports)

**10 of the 15 active rules are silent in `javac`** (valid code/configs that build with zero compiler warnings), while the other 5 catch broken/deprecated Boot 3 APIs in **~31 ms** before waiting on a 10–30 s Maven/Gradle build.

<details>
<summary>Browse all guides, compiler overlap, & version-gated rules</summary>

#### Java 17 / 21 / 25+ (`JAVA-*`)

| Rule / Guide | Min Version | Caught by `javac`? | Legacy → Modern Replacement |
| :--- | :--- | :--- | :--- |
| [`JAVA-001`](./src/modern_java_guidance/guides.py) | Java 8+ (scan 16+) | **No (silent)** | `new Date()` / `Calendar.getInstance()` / `SimpleDateFormat` → `java.time` (`Instant`, `LocalDate`, `DateTimeFormatter`) |
| [`JAVA-002`](./src/modern_java_guidance/guides.py) | Java 9+ (scan 16+) | **No (silent)** | `Collections.unmodifiableList(Arrays.asList(...))` → `List.of` / `Set.of` / `Map.of` |
| [`JAVA-003`](./src/modern_java_guidance/guides.py) | Java 15+ (scan 16+) | **No (silent)** | `String.format(...)` (without explicit `Locale`) → `"..." .formatted(...)` |
| [`JAVA-004`](./src/modern_java_guidance/guides.py) | Java 16+ | **No (silent)** | `.collect(Collectors.toList())` → `Stream.toList()` |
| [`JAVA-010`](./src/modern_java_guidance/guides.py) | Java 21+ | **No (silent)** | `Executors.newFixedThreadPool` / `newCachedThreadPool` → `Executors.newVirtualThreadPerTaskExecutor()` (blocking I/O) |
| [`JAVA-011`](./src/modern_java_guidance/guides.py) | Java 21+ | **No (silent)** | `list.get(list.size() - 1)` → `SequencedCollection.getLast()` |
| [`JAVA-012`](./src/modern_java_guidance/guides.py) | Java 21+ *(guide)* | **No (silent)** | Verbose POJOs / `instanceof` casts → `record`, `sealed interface`, Pattern Matching for `switch` |

#### Spring Boot 3.x+ & Security 6 (`BOOT-*`)

| Rule / Guide | Min Version | Caught by `javac`? | Legacy → Modern Replacement |
| :--- | :--- | :--- | :--- |
| [`BOOT-001`](./src/modern_java_guidance/guides.py) | Boot 3.0+ | Compile error *(build-time)* | `javax.{persistence,validation,servlet,annotation,transaction,inject,mail,xml.bind,ws.rs}.*` → `jakarta.*` |
| [`BOOT-002`](./src/modern_java_guidance/guides.py) | Boot 3.0+ | Compile error *(build-time)* | `extends WebSecurityConfigurerAdapter` → `@Bean SecurityFilterChain` |
| [`BOOT-003`](./src/modern_java_guidance/guides.py) | Boot 3.2+ | **No (silent)** | `RestTemplate` / `RestTemplateBuilder` → `RestClient` or `@HttpExchange` |
| [`BOOT-004`](./src/modern_java_guidance/guides.py) | Boot 3.0+ | **No (silent)** | `@Autowired` field injection (skips constructors & test classes) → constructor injection (`private final`) |
| [`BOOT-005`](./src/modern_java_guidance/guides.py) | Boot 3.0+ | Compile error *(build-time)* | `.antMatchers()` / `.mvcMatchers()` / `.authorizeRequests()` → `.authorizeHttpRequests(a -> a.requestMatchers(...))` |
| [`BOOT-006`](./src/modern_java_guidance/guides.py) | Boot 3.0+ | `@Deprecated` *(build-time)* | `.csrf().disable()` (single & multiline) → keep CSRF enabled by default; `.csrf(AbstractHttpConfigurer::disable)` only for non-browser credentials (e.g., Bearer JWT) |
| [`BOOT-007`](./src/modern_java_guidance/guides.py) | Boot 3.0+ *(guide)* | **No (silent)** | Custom ad-hoc error payloads → RFC 9457 `ProblemDetail` in `@RestControllerAdvice` |
| [`BOOT-008`](./src/modern_java_guidance/guides.py) | Boot 3.4+ | `@Deprecated` *(build-time)* | `@MockBean` / `@SpyBean` → `@MockitoBean` / `@MockitoSpyBean` |
| [`BOOT-009`](./src/modern_java_guidance/guides.py) | Boot 3.0+ *(build file)* | **No (silent)** | `spring-cloud-starter-sleuth` → Micrometer Tracing + OpenTelemetry OTLP |
| [`BOOT-010`](./src/modern_java_guidance/guides.py) | Boot 3.3+ *(Dockerfile)* | **No (silent)** | Unextracted fat-JAR `java -jar app.jar` → `-Djarmode=tools ... extract`, Buildpacks, or AppCDS |

</details>

### Safe Adoption of Modern Features

* **Version-Gated & Multi-Module Safe**: Walks multi-module Maven (`pom.xml` + BOM `<dependencyManagement>`), Gradle (`build.gradle(.kts)` + `JavaVersion.VERSION_1_8` + `libs.versions.toml`), and `.java-version` so legacy repos stay untouched.
* **Comment, String & Text-Block Aware**: Strips `//`, `/* ... */`, `"..."`, and `"""..."""` literals before scanning so docs, log messages, and comments never trigger false positives.
* **Inline Suppression & Smart Hook Severity**: Suppress intentional exceptions with `// mjg:ignore JAVA-010` (or `// mjg:ignore`). Claude Code hooks hard-block on `error` findings and send non-blocking advisory context for `warning`/`info` (pass `--strict` to block all).
* **Gotchas & Quirks**: Every guide retrieved via `mjg retrieve <ID>` includes a `## Caveat` section (e.g., do not use `record` for JPA `@Entity`, keep bounded pools for CPU-bound work, check `!isEmpty()` before `getLast()`).

---

## How It Works

1. **Activation**: The coding agent activates the `modern-java-guidance` skill (`4.8 KB`) for Java / Spring Boot tasks.
2. **Version Detection**: Runs `mjg detect .` to inspect `pom.xml`, `build.gradle(.kts)`, `gradle/libs.versions.toml`, or `.java-version`.
3. **On-Demand Guide Fetch**: Runs `mjg search "<topic>"` and `mjg retrieve <ID>` to pull exact Before/After code patterns and caveats into context without loading bloated markdown files.
4. **Post-Edit Hook (`PostToolUse`)**: Runs `mjg hook` automatically after every `.java` edit (~31 ms) and blocks or warns on legacy regressions.

> [!TIP]
> The CLI works **100% offline, private, and local** using only the Python 3.11+ standard library—no network calls, no API keys, and zero third-party supply-chain dependencies.

---

## How `mjg` Complements `javac`, IDEs, and Semgrep

`mjg` is designed to sit **upstream** of your compiler and CI analyzers—inside the AI agent's edit loop—not to replace them:

| Layer | Feedback Timing | Catches Silent Legacy Patterns? (`RestTemplate`, `@Autowired`, `new Date()`, `newFixedThreadPool`) | Works in Headless AI Agent Loops? |
| :--- | :--- | :--- | :--- |
| **`javac` / Maven / Gradle** | 10–30 s per build | ❌ Only compile errors & `@Deprecated` | ⚠️ Slow inner-loop feedback |
| **IDE (IntelliJ IDEA)** | Real-time for humans | ⚠️ Partial (requires interactive GUI) | ❌ Not available to headless CLI agents |
| **Semgrep (CI / PR gate)** | PR / CI pipeline | ✅ Full Java AST rules | ✅ Exported directly from `mjg` |
| **`mjg` `PostToolUse` Hook** | **~31 ms per `.java` edit** | ✅ **10/15 rules are silent in `javac`** + pre-build catch for the other 5 | ✅ Native Claude Code & Antigravity hooks |

### Use the Same Rules in Semgrep (CI & Non-Agent Workflows)

You can run the bundled Java AST Semgrep ruleset directly in CI—or generate a version-gated ruleset tailored to your repository's `pom.xml` / `build.gradle(.kts)`:

```bash
# Run the pre-generated Java 21 + Spring Boot 3.4+ Semgrep ruleset directly
semgrep --config https://raw.githubusercontent.com/wkd09/modern-java-guidance/main/rules/semgrep/modern-java-boot3.yaml .

# Or export a version-gated Semgrep ruleset matching your project's detected Java & Boot versions
mjg export --format semgrep --path . -o .semgrep/modern-java.yaml
semgrep --config .semgrep/modern-java.yaml .
```

All 13 Semgrep Java AST rules in [`rules/semgrep/modern-java-boot3.yaml`](./rules/semgrep/modern-java-boot3.yaml) are validated and unit-tested (`semgrep --validate` + `semgrep --test` against [`modern-java-boot3.java`](./rules/semgrep/modern-java-boot3.java)) in CI on every push.

---

## Alternative Installation Methods

* **Vercel Skills CLI (`npx skills`)**:
  ```bash
  npx skills add wkd09/modern-java-guidance
  ```
* **GitHub CLI**:
  ```bash
  gh skill install wkd09/modern-java-guidance
  ```
* **Google Antigravity (`PostToolUse` hook + global skill)**:
  ```bash
  mjg setup --target antigravity --dir .
  ```
* **Claude Code (`PostToolUse` hook returning `"decision": "block"`)**:
  ```bash
  mjg setup --target claude --dir .
  ```
* **uv / pip (CLI only)**:
  ```bash
  uv tool install git+https://github.com/wkd09/modern-java-guidance.git
  # or: pip install git+https://github.com/wkd09/modern-java-guidance.git
  ```

---

## Evals to prove this works well

Modeled after `GoogleChrome/modern-web-guidance`, we maintain an automated assertion-based evaluation suite ([`scripts/eval_suite.py`](./scripts/eval_suite.py)) and throughput benchmark ([`scripts/benchmark.py`](./scripts/benchmark.py)) run in CI on every push:

```text
[ Expert-authored rules & guides ]
        │
        ▼
[ Target task definitions ] ──> 6 Java / Spring Boot tasks (Unguided Legacy vs. Guided Modern)
        │
        ▼
[ Calibration & assertion ] ──> Checks required modern patterns, forbidden legacy patterns, & `mjg check`
        │
        ▼
[ A/B Eval & Benchmark ]    ──> Measures pass-rate uplift, false positives, & per-file latency
```

### Eval & benchmark results snapshot

#### 1. A/B Task Pass Rate (`python3 scripts/eval_suite.py`)

| Task | Target | Unguided Baseline | Guided + `mjg` Hook |
| :--- | :--- | :--- | :--- |
| `EVAL-01` Spring Security 6 Config | Java 21, Boot 3.3.4 | FAIL (3 findings) | **PASS** (0 findings) |
| `EVAL-02` Synchronous HTTP Client | Java 21, Boot 3.3.4 | FAIL (3 findings) | **PASS** (0 findings) |
| `EVAL-03` Jakarta EE Persistence/Validation | Java 21, Boot 3.3.4 | FAIL (2 findings) | **PASS** (0 findings) |
| `EVAL-04` Blocking I/O Concurrency | Java 21, Boot 3.3.4 | FAIL (1 finding) | **PASS** (0 findings) |
| `EVAL-05` SequencedCollection & `java.time` | Java 21, Boot 3.3.4 | FAIL (2 findings) | **PASS** (0 findings) |
| `EVAL-06` Legacy Compatibility Preservation | Java 8, Boot 2.7.18 | PASS (0 false positives) | **PASS** (0 false positives) |
| **Overall Pass Rate** | **6 tasks** | **16.7% (1/6)** | **100.0% (6/6, +83.3 pp)** |

#### 2. Comparison with Existing Java & Spring Boot Skills

| Skill / Repo | Initial `SKILL.md` Size | Executable CLI | Auto Version Detect | `PostToolUse` Hook | Zero IDE/MCP Deps |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`modern-java-guidance` (`mjg`)** | **4,960 bytes** | ✅ `mjg check` / `search` / `retrieve` / `export` | ✅ Multi-module Maven & Gradle | ✅ Antigravity & Claude | ✅ Python stdlib only |
| **`github/awesome-copilot`** (`java-springboot` + `spring-security`) | 9,737 bytes | ❌ Markdown only | ⚠️ Manual read | ❌ None | ✅ |
| **`Amplicode/spring-skills`** (`spring-security-configuration`) | 17,344 bytes | ❌ None | ⚠️ IntelliJ MCP | ❌ None | ❌ Requires IntelliJ MCP |
| **`Santoshrt999/Java-Claude-Skills`** (`java-modernization-review`) | 20,103 bytes | ❌ Markdown only | ❌ None | ❌ None | ✅ |

> Verified on `Santoshrt999/Java-Claude-Skills/examples`: `mjg` automatically detected Java 21 from `pom.xml` and flagged `TradeProcessor.java:15` (`Executors.newFixedThreadPool(10)` → `[JAVA-010]`).

#### 3. Throughput & Latency (`python3 scripts/benchmark.py`, Apple Silicon)

| Benchmark | Workload | Result |
| :--- | :--- | :--- |
| **Repo scan** (`detect` + `scan_target`) | 10 / 100 / 500 / 1,000 Java files | **3.10 ms** / **22.84 ms** / **105.24 ms** / **183.40 ms** (`0.183 ms/file`) |
| **Build file detection** | `pom.xml` / `build.gradle.kts` / `.java-version` | **0.059 ms** / **0.043 ms** / **0.045 ms** |
| **`PostToolUse` hook (in-process)** | Single `.java` file (50 runs) | **p50 0.257 ms** · p95 0.317 ms · max 0.373 ms |
| **CLI subprocess E2E (`mjg hook`)** | Full process spawn (10 runs) | **31.0 ms median** (30.5–86.3 ms) |

---

## Contributors & License

Found a bug, outdated pattern, or missing Java/Spring Boot rule? [Open an issue](https://github.com/wkd09/modern-java-guidance/issues) or submit a pull request.

Licensed under the [MIT License](./LICENSE).
