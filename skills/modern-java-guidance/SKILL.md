---
name: modern-java-guidance
description: >-
  Guides coding agents to write modern Java (17/21/25+) and Spring Boot (3.x+)
  code using version detection and the `mjg` CLI/Hook scanner instead of legacy
  Java 8 and Spring Boot 2.x patterns. Activate when writing, refactoring, or
  reviewing Java or Spring Boot projects.
---

# Modern Java & Spring Boot Guidance (CLI + Hook + Skill)

LLMs heavily default to **Java 8** and **Spring Boot 2.x** idioms (`javax.*`, `WebSecurityConfigurerAdapter`, `RestTemplate`, `@Autowired` field injection, `new Date()`, `list.get(list.size() - 1)`, `Executors.newFixedThreadPool`). Use this skill and the bundled `mjg` CLI to detect the project's actual versions and enforce modern equivalents without breaking legacy codebases.

---

## Step 1: Detect Project Versions First

Before writing or refactoring Java code, run `mjg detect` (or inspect `pom.xml` / `build.gradle.kts` / `build.gradle` / `.java-version`):

```bash
mjg detect .
```

- **Java <= 11**: Respect the project's configured Java version. Do **not** emit Java 17/21 syntax (`record`, `sealed`, `SequencedCollection`, Virtual Threads) or upgrade the build file unless explicitly requested.
- **Java 17**: Use `record`, `sealed` classes/interfaces, `switch` expressions, text blocks, `List.of`/`Map.of`, `var`, and `java.time`. Do not use Java 21 APIs (`SequencedCollection`, Virtual Threads, Record Patterns).
- **Java 21+ (or greenfield code)**: Use Java 21+ idioms including Pattern Matching for `switch`, Record Patterns, `SequencedCollection` (`getFirst()`, `getLast()`, `reversed()`), and Virtual Threads (`Executors.newVirtualThreadPerTaskExecutor()`).
- **Spring Boot 2.x**: Keep `javax.*` and existing Spring Security 5 / `RestTemplate` APIs unless migrating to Boot 3.
- **Spring Boot 3.0–3.1**: Use `jakarta.*`, `SecurityFilterChain` + Lambda DSL + `requestMatchers()`, and constructor injection. (`RestClient` is not available yet; keep `WebClient` or `RestTemplate`.)
- **Spring Boot 3.2+**: Also prefer `RestClient` / `@HttpExchange` over `RestTemplate`.

---

## Step 2: Legacy vs. Modern Decision Matrix

| Category | ❌ Legacy (Java 8 / Boot 2.x) | ✅ Modern Java 21+ / Spring Boot 3.x+ |
| :--- | :--- | :--- |
| **DTO / Value Objects** | Verbose POJO or `@Data` on immutable DTOs | `public record UserDto(Long id, String email) {}` |
| **Type Dispatch** | `if (x instanceof A) { A a = (A) x; ... }` | Pattern Matching for `switch` + `sealed interface` |
| **First / Last Element** | `list.get(0)`, `list.get(list.size() - 1)` | `list.getFirst()`, `list.getLast()`, `list.reversed()` |
| **I/O Concurrency** | `Executors.newFixedThreadPool(...)` for blocking I/O | `Executors.newVirtualThreadPerTaskExecutor()` |
| **Date & Time** | `new Date()`, `SimpleDateFormat` | `Instant.now()`, `LocalDate`, `DateTimeFormatter` (`java.time`) |
| **Collections** | `Collections.unmodifiableList(Arrays.asList(...))` | `List.of(...)`, `Set.of(...)`, `Map.of(...)` |
| **EE Packages (Boot 3+)** | `import javax.persistence.*`, `javax.validation.*` | `import jakarta.persistence.*`, `jakarta.validation.*` |
| **Spring Security 6** | `extends WebSecurityConfigurerAdapter`, `.antMatchers()`, `.csrf().disable()` | `@Bean SecurityFilterChain`, `.authorizeHttpRequests(a -> a.requestMatchers(...))`, `.csrf(AbstractHttpConfigurer::disable)` |
| **HTTP Client (Boot 3.2+)** | `new RestTemplate()` | `RestClient.builder()` or `@HttpExchange` |
| **Dependency Injection** | `@Autowired` field injection | Constructor injection with `private final` fields |

---

## Step 3: On-Demand Guides & References

For token-efficient lookups without loading full reference files, query the built-in catalog:
```bash
mjg search "<topic>"      # e.g. mjg search "security" or mjg search "virtual-threads"
mjg retrieve <GUIDE_ID>   # e.g. mjg retrieve BOOT-002
```

- **Java 17/21/25 Language & Stdlib Patterns**: Read [references/java-21-25-core.md](./references/java-21-25-core.md)
- **Spring Boot 3.x+ & Spring Security 6 Patterns**: Read [references/spring-boot-3x.md](./references/spring-boot-3x.md)

---

## Step 4: Verify With `mjg check` Before Finishing

After writing or editing `.java` files, run the version-aware scanner (or let the `PostToolUse` hook run it automatically):

```bash
mjg check src/
```

Fix all `error` findings (e.g. `javax.*`, `WebSecurityConfigurerAdapter`) and address `warning` findings unless an external ABI or concurrency constraint (e.g., CPU-bound bounded pool) requires keeping the existing pattern.
