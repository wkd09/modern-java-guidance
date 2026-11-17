# modern-java-guidance (`mjg`)

> **Version-aware CLI scanner, Post-Edit Hook, and Agent Skill** that stops AI coding agents from writing Java 8 and Spring Boot 2.x legacy code.

Unlike markdown-only skills, `modern-java-guidance` ships with an executable **CLI + Post-Edit Hook (`mjg`)** that:
1. **Auto-detects** your project's Java version and Spring Boot version from `pom.xml`, `build.gradle.kts`, `build.gradle`, or `.java-version`.
2. **Applies version-gated rules**: Java 8/11 projects won't get false-positive Java 21 warnings; Spring Boot 2.x projects won't get `jakarta.*` or `RestClient` errors; Java 21 + Spring Boot 3.x projects immediately catch `javax.*`, `WebSecurityConfigurerAdapter`, `RestTemplate`, `antMatchers()`, `.csrf().disable()`, `new Date()`, `list.get(list.size() - 1)`, and `Executors.newFixedThreadPool`.
3. **Runs automatically after every AI edit** via Antigravity (`PostToolUse` in `.agents/hooks.json`) or Claude Code (`PostToolUse` in `.claude/settings.json`).

---

## Installation

### 1. Agent Skill (`skills` CLI)
```bash
npx skills add wkd09/modern-java-guidance
```

### 2. CLI + Post-Edit Hook (`mjg`)
```bash
# Install from source (no third-party Python dependencies required)
pip install git+https://github.com/wkd09/modern-java-guidance.git

# Or with uv:
uv tool install git+https://github.com/wkd09/modern-java-guidance.git
```

### One-Command Setup (Skill + Post-Edit Hook)
```bash
# Install Antigravity global skill + .agents/hooks.json in current project
mjg setup --target antigravity

# Or configure both Antigravity and Claude Code
mjg setup --target all --dir /path/to/your/java-project
```

---

## CLI Usage

```bash
# 1. Detect Java & Spring Boot version from pom.xml / build.gradle(.kts)
mjg detect .
mjg detect . --json

# 2. Scan Java files using detected versions
mjg check src/

# 3. Override versions explicitly
mjg check src/ --java 21 --boot 3.3.0 --strict
```

---

## Rules Enforced

| Rule ID | Applies From | Legacy Pattern Detected | Modern Replacement |
| :--- | :--- | :--- | :--- |
| `JAVA-001` | Java 16+ | `new Date()`, `SimpleDateFormat` | `java.time` (`Instant`, `LocalDate`, `DateTimeFormatter`) |
| `JAVA-002` | Java 16+ | `Collections.unmodifiableList(Arrays.asList(...))` | `List.of(...)`, `Set.of(...)`, `Map.of(...)` |
| `JAVA-003` | Java 16+ | `String.format(...)` | `"..." .formatted(...)` |
| `JAVA-010` | Java 21+ | `Executors.newFixedThreadPool` / `newCachedThreadPool` | `Executors.newVirtualThreadPerTaskExecutor()` (I/O-bound) |
| `JAVA-011` | Java 21+ | `list.get(list.size() - 1)` | `SequencedCollection.getLast()` |
| `BOOT-001` | Boot 3.0+ | `import javax.{persistence,validation,servlet,...}.*` | `import jakarta.*` |
| `BOOT-002` | Boot 3.0+ | `extends WebSecurityConfigurerAdapter` | `@Bean SecurityFilterChain` |
| `BOOT-003` | Boot 3.2+ | `new RestTemplate()` / `RestTemplateBuilder` | `RestClient` / `@HttpExchange` |
| `BOOT-004` | Boot 3.0+ | `@Autowired` field injection | Constructor injection |
| `BOOT-005` | Boot 3.0+ | `.antMatchers()` / `.mvcMatchers()` / `.authorizeRequests()` | `.authorizeHttpRequests(a -> a.requestMatchers(...))` |
| `BOOT-006` | Boot 3.0+ | `.csrf().disable()` | `.csrf(AbstractHttpConfigurer::disable)` |

---

## Benchmarks

Measured with `python3 scripts/benchmark.py` (Apple Silicon, Python standard library only):

| Metric | Result |
| :--- | :--- |
| **10 Java files** (`detect` + `scan_target`) | **1.95 ms** (`0.195 ms/file`) |
| **100 Java files** | **17.55 ms** (`0.175 ms/file`) |
| **500 Java files** | **89.74 ms** (`0.179 ms/file`) |
| **PostToolUse Hook (in-process)** | **p50 0.269 ms** / p95 0.368 ms |
| **CLI Subprocess E2E (`mjg hook`)** | **31.0 ms median** |
| **Detection Accuracy (Java 21 + Boot 3.3)** | **11/11 rules detected**, 0 false positives on modern code or comments |

---

## License

MIT
