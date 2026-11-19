<div align="center">

<img src="./assets/logo.svg" width="88" height="88" alt="modern-java-guidance logo" />

# Modern Java Guidance

**Modern Java Guidance**는 **Java 17/21/25+** 및 **Spring Boot 3.x+** 모범 사례를 AI 코딩 에이전트에 직접 내장하는 에이전트 스킬 · CLI 스캐너 · `PostToolUse` 훅입니다. 에이전트가 Java 8 및 Spring Boot 2.x 레거시 패턴을 버리고 현대적인 프로덕션 코드를 작성하도록 유도합니다.

[![CI](https://github.com/wkd09/modern-java-guidance/actions/workflows/ci.yml/badge.svg)](https://github.com/wkd09/modern-java-guidance/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](./pyproject.toml)
[![Dependencies: Zero](https://img.shields.io/badge/dependencies-zero-success.svg)](./pyproject.toml)

[English](./README.md) | [한국어](./README.ko.md) | [简体中文](./README.zh-CN.md)

[스킬 가이드](./skills/modern-java-guidance/SKILL.md) · [Semgrep 규칙](./rules/semgrep/modern-java-boot3.yaml) · [A/B 평가 스위트](./scripts/eval_suite.py) · [벤치마크](./scripts/benchmark.py) · [이슈 제보](https://github.com/wkd09/modern-java-guidance/issues)

</div>

---

## Why? (왜 필요한가요?)

LLM 학습 데이터에는 과거 **Java 8 및 Spring Boot 2.x** 시절의 엔터프라이즈 코드가 압도적으로 많기 때문에, AI 코딩 에이전트는 최신 Java 21 + Spring Boot 3.x 프로젝트에서도 습관적으로 삭제된 `javax.*` 임포트, `WebSecurityConfigurerAdapter`, `RestTemplate`, 블로킹용 `Executors.newFixedThreadPool()`을 생성합니다.

모델이 최신 API의 존재를 알더라도 읽기 전용 마크다운 스킬만으로는 세션 중 레거시 회귀를 막기 어렵습니다. **Modern Java Guidance**는 오프라인 CLI와 `PostToolUse` 가드레일로 이 간극을 메웁니다:

* **모던 Java & Spring Boot API 유도**: `SecurityFilterChain` Lambda DSL, `RestClient`, `@HttpExchange`, `record`, `sealed interface`, `SequencedCollection`, Virtual Threads로 정확히 안내합니다.
* **버전 인식 안전성**: `pom.xml`, `build.gradle(.kts)`, `libs.versions.toml`, `.java-version`을 감지해 Java 8 / Boot 2.x 레거시 프로젝트에는 오탐 경고를 띄우지 않습니다.
* **결정론적 Post-Edit 가드레일**: `.java` 파일이 수정될 때마다 **약 38 ms** 만에(LLM 토큰 0) 자동 스캔해 레거시 회귀를 즉시 차단·경고합니다.

---

## Quickstart

```bash
curl -fsSL https://raw.githubusercontent.com/wkd09/modern-java-guidance/main/install.sh | bash
mjg setup --target all --dir /path/to/your/spring-boot-project
```

`mjg`(Python 3.11+, 외부 의존성 0개)를 설치하고 에이전트 스킬과 `PostToolUse` 훅을 한 번에 설정합니다. 다른 설치 방법은 아래 [Alternative Installation Methods](#alternative-installation-methods)를 참고하세요.

### 설치 없이 바로 써보기 (`uvx`)

```bash
# 관련 패턴 가이드 검색
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg search "security"

# ID로 Before/After 가이드 상세 조회
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg retrieve BOOT-002

# 코드베이스의 레거시 Java / Spring Boot 패턴 스캔
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg check .
```

---

## What's Included?

최신 **Java 17 / 21 / 25+**와 **Spring Boot 3.x+** 핵심 패턴을 다룹니다. 토큰 효율성을 위해 `SKILL.md`는 **4.8 KB**로 최소화하고, 상세 Before/After 가이드는 `mjg search` 및 `mjg retrieve`로 필요할 때만 조회합니다.

### Core Disciplines

* **🔒 Spring Security 6**: `SecurityFilterChain` `@Bean`, Lambda DSL, `authorizeHttpRequests()`, `requestMatchers()`, `AbstractHttpConfigurer::disable`.
* **🌐 모던 HTTP 클라이언트**: `RestTemplate` 대신 플루언트 `RestClient` 및 선언형 `@HttpExchange` 인터페이스(Spring Boot 3.2+).
* **⚡ Virtual Threads & 동시성**: 블로킹 I/O용 `Executors.newVirtualThreadPerTaskExecutor()` (CPU 바운드 작업 시 제한된 풀 유지 주의사항 포함).
* **🧩 모던 Java 문법**: `record`, `sealed interface`, `switch` 패턴 매칭, `SequencedCollection` (`getFirst()`, `getLast()`), `java.time`, `List.of`/`Map.of`, `String.formatted()`.
* **🏛️ Jakarta EE 10 & 깔끔한 DI**: `jakarta.*` 마이그레이션, `@Autowired` 필드 주입 대신 생성자 주입, RFC 9457 `ProblemDetail`.
* **🛡️ 레거시 호환성 보존**: `pom.xml`/`build.gradle(.kts)`가 Java 8/11 또는 Boot 2.x를 타겟으로 하면 Java 21 / Boot 3+ 규칙을 자동으로 비활성화합니다.

### 전체 목록 (온디맨드 가이드 17종 · 스캐너 규칙 15종 · Semgrep 13종)

**활성 규칙 15개 중 10개는 `javac`가 경고 없이 통과시키는 침묵(silent) 패턴**이며, 나머지 5개도 10–30초짜리 Maven/Gradle 빌드 전에 **~38 ms** 만에 즉시 차단합니다.

<details>
<summary>모든 가이드, 컴파일러 중복 여부, 및 버전 게이팅 규칙 보기</summary>

#### Java 17 / 21 / 25+ (`JAVA-*`)

| 규칙 / 가이드 | 최소 버전 | `javac` 검출 여부 | 레거시 → 모던 대체 패턴 |
| :--- | :--- | :--- | :--- |
| [`JAVA-001`](./src/modern_java_guidance/guides.py) | Java 8+ (스캔 16+) | **미검출 (침묵)** | `new Date()` / `Calendar.getInstance()` / `SimpleDateFormat` → `java.time` (`Instant`, `LocalDate`, `DateTimeFormatter`) |
| [`JAVA-002`](./src/modern_java_guidance/guides.py) | Java 9+ (스캔 16+) | **미검출 (침묵)** | `Collections.unmodifiableList(Arrays.asList(...))` → `List.of` / `Set.of` / `Map.of` |
| [`JAVA-003`](./src/modern_java_guidance/guides.py) | Java 15+ (스캔 16+) | **미검출 (침묵)** | `String.format(...)` (`Locale` 미지정 시) → `"..." .formatted(...)` |
| [`JAVA-004`](./src/modern_java_guidance/guides.py) | Java 16+ | **미검출 (침묵)** | `.collect(Collectors.toList())` → `Stream.toList()` |
| [`JAVA-010`](./src/modern_java_guidance/guides.py) | Java 21+ | **미검출 (침묵)** | `Executors.newFixedThreadPool` / `newCachedThreadPool` → `Executors.newVirtualThreadPerTaskExecutor()` (블로킹 I/O) |
| [`JAVA-011`](./src/modern_java_guidance/guides.py) | Java 21+ | **미검출 (침묵)** | `list.get(list.size() - 1)` → `SequencedCollection.getLast()` |
| [`JAVA-012`](./src/modern_java_guidance/guides.py) | Java 21+ *(가이드)* | **미검출 (침묵)** | 장황한 POJO / `instanceof` 캐스팅 → `record`, `sealed interface`, `switch` 패턴 매칭 |

#### Spring Boot 3.x+ & Security 6 (`BOOT-*`)

| 규칙 / 가이드 | 최소 버전 | `javac` 검출 여부 | 레거시 → 모던 대체 패턴 |
| :--- | :--- | :--- | :--- |
| [`BOOT-001`](./src/modern_java_guidance/guides.py) | Boot 3.0+ | 컴파일 에러 *(빌드 시)* | `javax.{persistence,validation,servlet,annotation,transaction,inject,mail,xml.bind,ws.rs}.*` → `jakarta.*` |
| [`BOOT-002`](./src/modern_java_guidance/guides.py) | Boot 3.0+ | 컴파일 에러 *(빌드 시)* | `extends WebSecurityConfigurerAdapter` → `@Bean SecurityFilterChain` |
| [`BOOT-003`](./src/modern_java_guidance/guides.py) | Boot 3.2+ | **미검출 (침묵)** | `RestTemplate` / `RestTemplateBuilder` → `RestClient` 또는 `@HttpExchange` |
| [`BOOT-004`](./src/modern_java_guidance/guides.py) | Boot 3.0+ | **미검출 (침묵)** | `@Autowired` 필드 주입 (생성자·테스트 클래스 자동 제외) → 생성자 주입 (`private final`) |
| [`BOOT-005`](./src/modern_java_guidance/guides.py) | Boot 3.0+ | 컴파일 에러 *(빌드 시)* | `.antMatchers()` / `.mvcMatchers()` / `.authorizeRequests()` → `.authorizeHttpRequests(a -> a.requestMatchers(...))` |
| [`BOOT-006`](./src/modern_java_guidance/guides.py) | Boot 3.0+ | `@Deprecated` *(빌드 시)* | `.csrf().disable()` (단일/멀티라인) → 기본 CSRF 유지; 브라우저 비연동 인증(Bearer JWT 등)에 한해 `.csrf(AbstractHttpConfigurer::disable)` |
| [`BOOT-007`](./src/modern_java_guidance/guides.py) | Boot 3.0+ *(가이드)* | **미검출 (침묵)** | 임의 에러 JSON → `@RestControllerAdvice`에서 RFC 9457 `ProblemDetail` 반환 |
| [`BOOT-008`](./src/modern_java_guidance/guides.py) | Boot 3.4+ | `@Deprecated` *(빌드 시)* | `@MockBean` / `@SpyBean` → `@MockitoBean` / `@MockitoSpyBean` |
| [`BOOT-009`](./src/modern_java_guidance/guides.py) | Boot 3.0+ *(빌드 파일)* | **미검출 (침묵)** | `spring-cloud-starter-sleuth` → Micrometer Tracing + OpenTelemetry OTLP |
| [`BOOT-010`](./src/modern_java_guidance/guides.py) | Boot 3.3+ *(Dockerfile)* | **미검출 (침묵)** | 단순 fat-JAR `java -jar app.jar` → `-Djarmode=tools ... extract`, Buildpacks 또는 AppCDS |

</details>

### Safe Adoption of Modern Features

* **멀티모듈 버전 게이팅**: 멀티모듈 Maven (`pom.xml` + BOM `<dependencyManagement>`), Gradle (`build.gradle(.kts)` + `JavaVersion.VERSION_1_8` + `libs.versions.toml`), `.java-version`을 상위까지 병합 감지해 레거시 오탐을 방지합니다.
* **주석·문자열·텍스트 블록 인식 스캔**: `//`, `/* ... */`, `"..."`, `"""..."""` 내부 텍스트를 제거한 뒤 스캔하여 로그 문구나 주석으로 인한 오탐을 차단합니다.
* **인라인 예외 처리 및 훅 심각도 분리**: 의도적 예외는 `// mjg:ignore JAVA-010`(또는 `// mjg:ignore`)로 억제할 수 있으며, Claude Code 훅은 `error`만 하드 블록하고 `warning`/`info`는 비차단 컨텍스트로 전달합니다(`--strict`로 전체 차단 가능).
* **주의사항(Caveats) 제공**: `mjg retrieve <ID>`로 조회 시 실무 함정(예: JPA `@Entity`에 `record` 사용 금지, `getLast()` 전 빈 리스트 확인)을 함께 제공합니다.

---

## How It Works

1. **Activation**: Java/Spring Boot 작업 시 에이전트가 `modern-java-guidance` 스킬(`4.8 KB`)을 활성화합니다.
2. **Version Detection**: `mjg detect .`로 `pom.xml`, `build.gradle(.kts)`, `gradle/libs.versions.toml`, `.java-version`을 파싱합니다.
3. **On-Demand Guide Fetch**: `mjg search "<topic>"`와 `mjg retrieve <ID>`로 필요한 Before/After 패턴과 주의사항만 컨텍스트에 불러옵니다.
4. **Post-Edit Hook (`PostToolUse`)**: `.java` 파일이 수정될 때마다 `mjg hook`이 ~38 ms 만에 실행되어 레거시 회귀를 차단·경고합니다.

> [!TIP]
> `mjg` CLI는 Python 3.11+ 표준 라이브러리만으로 **100% 오프라인·로컬 환경**에서 동작하며 외부 네트워크 호출이나 API 키, 서드파티 의존성이 전혀 없습니다.

---

## `javac`, IDE, Semgrep과의 역할 분담

`mjg`는 컴파일러나 기존 정적 분석기를 대체하는 도구가 아니라, **AI 코딩 에이전트의 파일 수정 직후(빌드 이전)** 단계를 보완하는 앞단 가드레일입니다:

| 계층 | 피드백 시점 | 침묵 레거시 패턴 검출? (`RestTemplate`, `@Autowired`, `new Date()`, `newFixedThreadPool`) | 헤드리스 AI 에이전트 루프 지원? |
| :--- | :--- | :--- | :--- |
| **`javac` / Maven / Gradle** | 빌드당 10–30초 | ❌ 컴파일 에러 및 `@Deprecated`만 검출 | ⚠️ 내부 편집 루프에 쓰기엔 느림 |
| **IDE (IntelliJ IDEA)** | 사람 편집 시 실시간 | ⚠️ 부분 지원 (GUI 환경 필요) | ❌ 헤드리스 CLI 에이전트에서 사용 불가 |
| **Semgrep (CI / PR 게이트)** | PR / CI 파이프라인 | ✅ Java AST 기반 정밀 분석 | ✅ `mjg`에서 규칙 바로 내보내기 가능 |
| **`mjg` `PostToolUse` 훅** | **`.java` 수정당 ~38 ms** | ✅ **15개 중 10개가 `javac` 미검출 규칙** + 나머지 5개 빌드 전 즉시 차단 | ✅ Claude Code & Antigravity 네이티브 훅 |

### Semgrep 규칙으로 CI 및 일반 워크플로우에서도 재사용하기

내장된 Java AST Semgrep 규칙을 CI에서 바로 실행하거나, 현재 프로젝트의 `pom.xml` / `build.gradle(.kts)` 버전에 맞춘 규칙 파일만 선택적으로 내보낼 수 있습니다:

```bash
# Java 21 + Spring Boot 3.4+ 기본 Semgrep 규칙 바로 실행
semgrep --config https://raw.githubusercontent.com/wkd09/modern-java-guidance/main/rules/semgrep/modern-java-boot3.yaml .

# 또는 현재 프로젝트 버전에 맞춘 버전 게이팅 Semgrep YAML 생성
mjg export --format semgrep --path . -o .semgrep/modern-java.yaml
semgrep --config .semgrep/modern-java.yaml .
```

[`rules/semgrep/modern-java-boot3.yaml`](./rules/semgrep/modern-java-boot3.yaml)의 13개 Java AST 규칙은 모두 CI에서 `semgrep --validate`와 `semgrep --test`([`modern-java-boot3.java`](./rules/semgrep/modern-java-boot3.java))로 자동 검증됩니다.

---

## Alternative Installation Methods

* **Vercel Skills CLI (`npx skills`)**: `npx skills add wkd09/modern-java-guidance`
* **GitHub CLI**: `gh skill install wkd09/modern-java-guidance`
* **Google Antigravity**: `mjg setup --target antigravity --dir .`
* **Claude Code**: `mjg setup --target claude --dir .`
* **uv / pip (CLI 단독)**:
  ```bash
  uv tool install git+https://github.com/wkd09/modern-java-guidance.git
  # 또는: pip install git+https://github.com/wkd09/modern-java-guidance.git
  ```

---

## Evals to prove this works well

`GoogleChrome/modern-web-guidance`의 폐쇄형 검증 파이프라인을 모델로 하여, CI에서 매 푸시마다 자동 실행되는 Assertion 기반 평가 스위트([`scripts/eval_suite.py`](./scripts/eval_suite.py))와 성능 벤치마크([`scripts/benchmark.py`](./scripts/benchmark.py))를 운영합니다:

```text
[ 전문가 작성 규칙 & 가이드 ]
        │
        ▼
[ 타겟 태스크 정의 ]      ──> 6개 Java / Spring Boot 태스크 (Unguided Legacy vs. Guided Modern)
        │
        ▼
[ 캘리브레이션 & 채점 ]   ──> 필수 모던 패턴, 금지 레거시 패턴, `mjg check` 통과 여부 검증
        │
        ▼
[ A/B 평가 & 벤치마크 ]   ──> 통과율 향상폭(+pp), 오탐률, 파일당 지연시간 측정
```

### Eval & benchmark results snapshot

#### 1. A/B 태스크 통과율 (`python3 scripts/eval_suite.py`)

| 태스크 | 타겟 환경 | 비유도 베이스라인 | 가이드 + `mjg` 훅 |
| :--- | :--- | :--- | :--- |
| `EVAL-01` Spring Security 6 설정 | Java 21, Boot 3.3.4 | FAIL (3건 검출) | **PASS** (0건) |
| `EVAL-02` 동기 HTTP 클라이언트 | Java 21, Boot 3.3.4 | FAIL (2건 검출) | **PASS** (0건) |
| `EVAL-03` Jakarta EE 영속성/검증 | Java 21, Boot 3.3.4 | FAIL (2건 검출) | **PASS** (0건) |
| `EVAL-04` 블로킹 I/O 동시성 | Java 21, Boot 3.3.4 | FAIL (1건 검출) | **PASS** (0건) |
| `EVAL-05` SequencedCollection & `java.time` | Java 21, Boot 3.3.4 | FAIL (2건 검출) | **PASS** (0건) |
| `EVAL-06` 레거시 호환성 보존 | Java 8, Boot 2.7.18 | PASS (오탐 0건) | **PASS** (오탐 0건) |
| **전체 통과율 (Pass Rate)** | **6개 태스크** | **16.7% (1/6)** | **100.0% (6/6, +83.3%p)** |

#### 2. 기존 Java / Spring Boot 스킬 비교

| 스킬 / 저장소 | 초기 `SKILL.md` 크기 | 실행형 CLI | 버전 자동 감지 | `PostToolUse` 훅 | IDE/MCP 무의존 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`modern-java-guidance` (`mjg`)** | **4,960 bytes** | ✅ `mjg check` / `search` / `retrieve` / `export` | ✅ 멀티모듈 Maven & Gradle | ✅ Antigravity & Claude | ✅ Python 표준 라이브러리만 |
| **`github/awesome-copilot`** (`java-springboot` + `spring-security`) | 9,737 bytes | ❌ 마크다운만 | ⚠️ 수동 읽기 | ❌ 없음 | ✅ |
| **`Amplicode/spring-skills`** (`spring-security-configuration`) | 17,344 bytes | ❌ 없음 | ⚠️ IntelliJ MCP | ❌ 없음 | ❌ IntelliJ MCP 필수 |
| **`Santoshrt999/Java-Claude-Skills`** (`java-modernization-review`) | 20,103 bytes | ❌ 마크다운만 | ❌ 없음 | ❌ 없음 | ✅ |

> `Santoshrt999/Java-Claude-Skills/examples` 실측: `mjg`가 `pom.xml`에서 Java 21을 자동 감지하고 `TradeProcessor.java:15`의 `Executors.newFixedThreadPool(10)` (`[JAVA-010]`)을 즉시 검출했습니다.

#### 3. 처리량 및 지연시간 (`python3 scripts/benchmark.py`, `v0.2.1`, Apple Silicon)

| 벤치마크 | 규모 / 조건 | 실측 결과 |
| :--- | :--- | :--- |
| **저장소 스캔** (`detect` + `scan_target`) | 10 / 100 / 500 / 1,000개 Java 파일 | **3.96 ms** / **29.23 ms** / **156.78 ms** / **324.54 ms** (`0.325 ms/file`) |
| **빌드 파일 버전 감지** | `pom.xml` / `build.gradle.kts` / `.java-version` | **0.072 ms** / **0.060 ms** / **0.186 ms** |
| **`PostToolUse` 훅 (인프로세스)** | 단일 `.java` 파일 (50회) | **p50 0.407 ms** · p95 0.932 ms · max 1.019 ms |
| **CLI 서브프로세스 E2E (`mjg hook`)** | 전체 프로세스 실행 (10회) | **중앙값 37.7 ms** (35.9–66.2 ms) |

---

## Contributors & License

버그 제보나 새로운 Java/Spring Boot 규칙 제안은 [이슈 등록](https://github.com/wkd09/modern-java-guidance/issues) 또는 PR로 참여해 주세요.

[MIT License](./LICENSE)에 따라 배포됩니다.
