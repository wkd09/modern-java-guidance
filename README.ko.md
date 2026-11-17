<div align="center">

<img src="./assets/logo.svg" width="88" height="88" alt="modern-java-guidance logo" />

# Modern Java Guidance (`mjg`)

**Modern Java Guidance**는 AI 코딩 에이전트에 **Java 17/21/25+** 및 **Spring Boot 3.x+** 모범 사례를 직접 주입하는 버전 인식 CLI 스캐너 · `PostToolUse` 훅 · 에이전트 스킬입니다.

[![CI](https://github.com/wkd09/modern-java-guidance/actions/workflows/ci.yml/badge.svg)](https://github.com/wkd09/modern-java-guidance/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](./pyproject.toml)
[![Dependencies: Zero](https://img.shields.io/badge/dependencies-zero-success.svg)](./pyproject.toml)

[English](./README.md) | [한국어](./README.ko.md) | [简体中文](./README.zh-CN.md)

</div>

---

## 왜 Modern Java Guidance인가요?

LLM 학습 데이터의 상당수가 **Java 8 및 Spring Boot 2.x** 시절 코드로 채워져 있기 때문에, AI 코딩 에이전트는 새 Java 21 + Spring Boot 3.x 프로젝트에서도 습관적으로 삭제된 `javax.*` 임포트, `WebSecurityConfigurerAdapter`, `RestTemplate`, `Executors.newFixedThreadPool()`을 생성합니다.

모델이 최신 API의 존재를 알더라도 읽기 전용 마크다운 스킬만으로는 세션 중 레거시 회귀를 막기 어렵습니다. Modern Java Guidance는 실행형 CLI와 `PostToolUse` 가드레일로 이 간극을 메웁니다:

* **버전 인식 자동 감지 (`mjg detect`)**: `pom.xml`, `build.gradle(.kts)`, `gradle/libs.versions.toml`, `.java-version`을 파싱해 Java 8 / Boot 2.x 레거시 프로젝트에는 오탐 경고를 띄우지 않습니다.
* **온디맨드 패턴 검색/조회 (`mjg search` / `mjg retrieve`)**: `SKILL.md`를 **4.1 KB**로 가볍게 유지하면서 필요한 Before/After 코드만 즉시 조회합니다.
* **결정론적 Post-Edit 가드레일 (`mjg hook`)**: 에이전트가 `.java` 파일을 수정할 때마다 **약 31 ms** 만에(LLM 토큰 0) 자동 스캔하고 레거시 코드를 차단·경고합니다.

---

## 빠른 시작

한 줄로 `mjg`를 설치합니다 (Python 3.11+, 외부 의존성 0개):

```bash
curl -fsSL https://raw.githubusercontent.com/wkd09/modern-java-guidance/main/install.sh | bash
```

Java/Spring Boot 프로젝트에 스킬과 `PostToolUse` 훅을 연결합니다:

```bash
mjg setup --target all --dir /path/to/your/spring-boot-project
```

### 설치 없이 바로 써보기 (`uvx`)

```bash
# pom.xml / build.gradle(.kts) 버전 기준으로 프로젝트 즉시 스캔
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg check .

# 키워드로 모던 Java/Spring 가이드 검색
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg search "security"

# 특정 가이드 ID의 Before/After 코드 조회
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg retrieve BOOT-002
```

---

## 에이전트 및 도구 연동

* **Vercel Agent Skills (Claude Code, Cursor, Copilot, Codex, Antigravity)**:
  ```bash
  npx skills add wkd09/modern-java-guidance
  ```
* **Antigravity (`PostToolUse` 훅 + 글로벌 스킬)**:
  ```bash
  mjg setup --target antigravity --dir .
  ```
* **Claude Code (`"decision": "block"` 반환 `PostToolUse` 훅)**:
  ```bash
  mjg setup --target claude --dir .
  ```

<details>
<summary>생성되는 훅 설정 보기 (<code>.claude/settings.json</code> / <code>.agents/hooks.json</code>)</summary>

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

## 포함된 내용

* **Java 17 / 21 / 25+ 언어 및 표준 라이브러리**: `record`, `sealed interface`, `switch` 패턴 매칭, `SequencedCollection` (`getFirst()`, `getLast()`), Virtual Threads (`Executors.newVirtualThreadPerTaskExecutor()`), `java.time`, 불변 컬렉션 팩토리(`List.of`, `Map.of`), `String.formatted()`.
* **Spring Boot 3.x+ & Spring Security 6**: `jakarta.*` (Jakarta EE 10) 마이그레이션, `SecurityFilterChain` Lambda DSL (`authorizeHttpRequests`, `requestMatchers`, `AbstractHttpConfigurer::disable`), `RestClient` & `@HttpExchange` (Boot 3.2+), 생성자 주입, RFC 9457 `ProblemDetail`.
* **레거시 호환성 보존**: `pom.xml`이나 `build.gradle(.kts)`가 Java 8/11 또는 Boot 2.x를 타겟으로 하면 Java 21 / Boot 3+ 규칙을 자동으로 비활성화합니다.

<details>
<summary>전체 버전 게이팅 규칙 목록 (실행형 스캐너 규칙 11종 + 온디맨드 가이드 13종)</summary>

| 규칙 ID | 심각도 | 적용 기준 | 검출하는 레거시 패턴 | 권장 모던 패턴 |
| :--- | :--- | :--- | :--- | :--- |
| `JAVA-001` | `warning` | Java 16+ | `new Date()`, `SimpleDateFormat` | `java.time` (`Instant`, `LocalDate`, `DateTimeFormatter`) |
| `JAVA-002` | `warning` | Java 16+ | `Collections.unmodifiableList(Arrays.asList(...))` | `List.of(...)`, `Set.of(...)`, `Map.of(...)` |
| `JAVA-003` | `info` | Java 16+ | `String.format(...)` | `"..." .formatted(...)` |
| `JAVA-010` | `warning` | Java 21+ | `Executors.newFixedThreadPool` / `newCachedThreadPool` | `Executors.newVirtualThreadPerTaskExecutor()` (I/O 바운드) |
| `JAVA-011` | `warning` | Java 21+ | `list.get(list.size() - 1)` | `SequencedCollection.getLast()` |
| `BOOT-001` | `error` | Boot 3.0+ | `import javax.{persistence,validation,servlet,...}.*` | `import jakarta.*` |
| `BOOT-002` | `error` | Boot 3.0+ | `extends WebSecurityConfigurerAdapter` | `@Bean SecurityFilterChain` |
| `BOOT-003` | `warning` | Boot 3.2+ | `RestTemplate` / `RestTemplateBuilder` | `RestClient` / `@HttpExchange` |
| `BOOT-004` | `warning` | Boot 3.0+ | `@Autowired` 필드 주입 | 생성자 주입 |
| `BOOT-005` | `error` | Boot 3.0+ | `.antMatchers()` / `.mvcMatchers()` / `.authorizeRequests()` | `.authorizeHttpRequests(a -> a.requestMatchers(...))` |
| `BOOT-006` | `error` | Boot 3.0+ | `.csrf().disable()` | `.csrf(AbstractHttpConfigurer::disable)` |

</details>

---

## 평가 및 벤치마크

### 1. Assertion 기반 A/B 평가 (`scripts/eval_suite.py`)

`GoogleChrome/modern-web-guidance`의 Assertion 채점 방식을 참고해, **6개 대표 Java / Spring Boot 태스크**에 대해 **비유도 레거시 베이스라인(Unguided)** vs **가이드 + `mjg` 훅 적용(Guided)** 결과를 비교 검증했습니다:

| 지표 | 비유도 레거시 베이스라인 | 가이드 + `mjg` 훅 적용 | 향상폭 (Uplift) |
| :--- | :--- | :--- | :--- |
| **전체 태스크 통과율 (Pass Rate)** | **1 / 6 (16.7%)** | **6 / 6 (100.0%)** | **+83.3%p** |

| 태스크 | 타겟 환경 | 비유도 베이스라인 | 가이드 + `mjg` 훅 |
| :--- | :--- | :--- | :--- |
| `EVAL-01` Spring Security 6 설정 | Java 21, Boot 3.3.4 | FAIL (`mjg` 3건 검출) | **PASS** (0건) |
| `EVAL-02` 동기 HTTP 클라이언트 | Java 21, Boot 3.3.4 | FAIL (`mjg` 3건 검출) | **PASS** (0건) |
| `EVAL-03` Jakarta EE 영속성/검증 | Java 21, Boot 3.3.4 | FAIL (`mjg` 2건 검출) | **PASS** (0건) |
| `EVAL-04` 블로킹 I/O 동시성 | Java 21, Boot 3.3.4 | FAIL (`mjg` 1건 검출) | **PASS** (0건) |
| `EVAL-05` SequencedCollection & `java.time` | Java 21, Boot 3.3.4 | FAIL (`mjg` 2건 검출) | **PASS** (0건) |
| `EVAL-06` 레거시 호환성 보존 | Java 8, Boot 2.7.18 | PASS (오탐 0건) | **PASS** (오탐 0건) |

### 2. 기존 Java / Spring Boot 스킬 비교

| 비교 항목 | **`modern-java-guidance` (`mjg`)** | **`github/awesome-copilot`**<br>(`java-springboot` + `spring-security`) | **`Amplicode/spring-skills`**<br>(`spring-security-configuration`) | **`Santoshrt999/Java-Claude-Skills`**<br>(`java-modernization-review`) |
| :--- | :--- | :--- | :--- | :--- |
| **초기 `SKILL.md` 크기** | **4,157 bytes** | 9,737 bytes (4,433 + 5,304) | 17,344 bytes (4.2배) | 20,103 bytes (4.8배) |
| **실행형 CLI 스캐너** | ✅ `mjg check` (LLM 토큰 0) | ❌ 마크다운 문서만 | ❌ 없음 | ❌ 마크다운 문서만 |
| **자동 버전 감지** | ✅ `mjg detect` (`pom.xml` / Gradle) | ⚠️ 수동 읽기 | ⚠️ IntelliJ MCP 필수 | ❌ 없음 |
| **`PostToolUse` 자동 차단 훅** | ✅ Antigravity & Claude Code | ❌ 없음 | ❌ 없음 | ❌ 없음 |
| **외부 / IDE 의존성** | **없음** (Python 표준 라이브러리만) | 없음 | ❌ IntelliJ Amplicode MCP | 없음 |

### 3. 처리량 및 지연시간 (`scripts/benchmark.py`)

Apple Silicon 실측 결과 (Python 표준 라이브러리만 사용):

| 벤치마크 항목 | 규모 / 조건 | 실측 결과 |
| :--- | :--- | :--- |
| **저장소 스캔** (`detect` + `scan_target`) | 10 / 100 / 500 / 1,000개 Java 파일 | **3.10 ms** / **22.84 ms** / **105.24 ms** / **183.40 ms** (`0.183 ms/file`) |
| **빌드 파일 버전 감지** | `pom.xml` / `build.gradle.kts` / `.java-version` | **0.059 ms** / **0.043 ms** / **0.045 ms** |
| **`PostToolUse` 훅 (인프로세스)** | 단일 `.java` 파일 (50회) | **p50 0.257 ms** · p95 0.317 ms · max 0.373 ms |
| **CLI 서브프로세스 E2E (`mjg hook`)** | 전체 프로세스 실행 (10회) | **중앙값 31.0 ms** (30.5–86.3 ms) |

---

## 라이선스

[MIT](./LICENSE)
