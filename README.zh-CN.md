<div align="center">

<img src="./assets/logo.svg" width="88" height="88" alt="modern-java-guidance logo" />

# Modern Java Guidance

**Modern Java Guidance** 是一套将 **Java 17/21/25+** 与 **Spring Boot 3.x+** 最佳实践直接嵌入 AI 编程助手的 Agent Skill、CLI 扫描器与 `PostToolUse` Hook，引导编程助手告别 Java 8 与 Spring Boot 2.x 遗留写法，转向现代生产级实现。

[![CI](https://github.com/wkd09/modern-java-guidance/actions/workflows/ci.yml/badge.svg)](https://github.com/wkd09/modern-java-guidance/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](./pyproject.toml)
[![Dependencies: Zero](https://img.shields.io/badge/dependencies-zero-success.svg)](./pyproject.toml)

[English](./README.md) | [한국어](./README.ko.md) | [简体中文](./README.zh-CN.md)

[Skill 指南](./skills/modern-java-guidance/SKILL.md) · [A/B 评估套件](./scripts/eval_suite.py) · [性能基准](./scripts/benchmark.py) · [提交 Issue](https://github.com/wkd09/modern-java-guidance/issues)

</div>

---

## Why?（为什么需要它？）

LLM 训练数据中充斥着大量 **Java 8 与 Spring Boot 2.x** 时期的企业遗留代码，因此即便在全新的 Java 21 + Spring Boot 3.x 项目中，AI 编程助手也经常默认输出已被移除的 `javax.*` 导入、`WebSecurityConfigurerAdapter`、`RestTemplate` 或阻塞式 `Executors.newFixedThreadPool()`。

即使模型知道现代 API 的存在，单纯的静态 Markdown 提示词也无法阻止长对话中的回退。**Modern Java Guidance** 通过离线 CLI 与 `PostToolUse` 护栏弥合了这一差距：

* **现代 Java & Spring Boot API 引导**：准确引导模型使用 `SecurityFilterChain` Lambda DSL、`RestClient`、`@HttpExchange`、`record`、`sealed interface`、`SequencedCollection` 与虚拟线程。
* **版本感知安全门控**：自动解析 `pom.xml`、`build.gradle(.kts)`、`libs.versions.toml` 与 `.java-version`，确保 Java 8 / Boot 2.x 老项目不会触发误报。
* **确定性编辑后护栏**：每次修改 `.java` 文件后仅需 **~31 ms**（零 LLM Token）即可完成扫描并拦截过时写法。

---

## Quickstart

```bash
curl -fsSL https://raw.githubusercontent.com/wkd09/modern-java-guidance/main/install.sh | bash
mjg setup --target all --dir /path/to/your/spring-boot-project
```

该命令会安装 `mjg`（Python 3.11+，零第三方依赖）并自动配置 Agent Skill 与 `PostToolUse` Hook。其他安装方式见下文 [Alternative Installation Methods](#alternative-installation-methods)。

### 免安装直接体验（`uvx`）

```bash
# 按关键字搜索现代写法指南
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg search "security"

# 按 ID 获取详细 Before/After 指南
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg retrieve BOOT-002

# 扫描项目中的过时 Java / Spring Boot 写法
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg check .
```

---

## What's Included?

涵盖现代 **Java 17 / 21 / 25+** 与 **Spring Boot 3.x+** 核心实践。`SKILL.md` 仅 **4.1 KB**，详细的前后对比示例通过 `mjg search` 与 `mjg retrieve` 按需加载。

### Core Disciplines

* **🔒 Spring Security 6**：`SecurityFilterChain` `@Bean`、Lambda DSL、`authorizeHttpRequests()`、`requestMatchers()` 与 `AbstractHttpConfigurer::disable`。
* **🌐 现代 HTTP 客户端**：使用流式 `RestClient` 与声明式 `@HttpExchange`（Spring Boot 3.2+）替代 `RestTemplate`。
* **⚡ 虚拟线程与并发**：I/O 密集型任务使用 `Executors.newVirtualThreadPerTaskExecutor()`（附带 CPU 密集型有界池注意事项）。
* **🧩 现代 Java 语法**：`record`、`sealed interface`、`switch` 模式匹配、`SequencedCollection`（`getFirst()`、`getLast()`）、`java.time`、`List.of`/`Map.of` 与 `String.formatted()`。
* **🏛️ Jakarta EE 10 与依赖注入**：`jakarta.*` 迁移、构造函数注入替代 `@Autowired` 字段注入，以及 RFC 9457 `ProblemDetail`。
* **🛡️ 旧版本兼容性保护**：当 `pom.xml` 或 `build.gradle(.kts)` 面向 Java 8/11 或 Boot 2.x 时，自动关闭 Java 21 与 Boot 3+ 规则。

### 完整规则与指南清单（13 篇指南 & 11 条可执行扫描规则）

<details>
<summary>查看所有指南与版本门控规则</summary>

#### Java 17 / 21 / 25+ (`JAVA-*`)
* [`JAVA-001`](./src/modern_java_guidance/guides.py) *(Java 8+ / 扫描 16+)*：`java.util.Date` & `SimpleDateFormat` → `java.time` (`Instant`, `LocalDate`, `DateTimeFormatter`)。
* [`JAVA-002`](./src/modern_java_guidance/guides.py) *(Java 9+ / 扫描 16+)*：`Collections.unmodifiableList(Arrays.asList(...))` → `List.of` / `Set.of` / `Map.of`。
* [`JAVA-003`](./src/modern_java_guidance/guides.py) *(Java 15+ / 扫描 16+)*：`String.format(...)` → `"..." .formatted(...)`。
* [`JAVA-010`](./src/modern_java_guidance/guides.py) *(Java 21+)*：阻塞 I/O 使用 `Executors.newVirtualThreadPerTaskExecutor()`。
* [`JAVA-011`](./src/modern_java_guidance/guides.py) *(Java 21+)*：`list.get(list.size() - 1)` → `SequencedCollection.getFirst()` / `getLast()`。
* [`JAVA-012`](./src/modern_java_guidance/guides.py) *(Java 21+, 指南)*：`record`、`sealed interface` 与 `switch` 模式匹配。

#### Spring Boot 3.x+ & Security 6 (`BOOT-*`)
* [`BOOT-001`](./src/modern_java_guidance/guides.py) *(Boot 3.0+)*：`javax.{persistence,validation,servlet,annotation,transaction}.*` → `jakarta.*`。
* [`BOOT-002`](./src/modern_java_guidance/guides.py) *(Boot 3.0+)*：`WebSecurityConfigurerAdapter` → `@Bean SecurityFilterChain`。
* [`BOOT-003`](./src/modern_java_guidance/guides.py) *(Boot 3.2+)*：`RestTemplate` → `RestClient` 或 `@HttpExchange`。
* [`BOOT-004`](./src/modern_java_guidance/guides.py) *(Boot 3.0+)*：`@Autowired` 字段注入 → 构造函数注入（`private final`）。
* [`BOOT-005`](./src/modern_java_guidance/guides.py) *(Boot 3.0+)*：`.antMatchers()` / `.mvcMatchers()` / `.authorizeRequests()` → `.authorizeHttpRequests(a -> a.requestMatchers(...))`。
* [`BOOT-006`](./src/modern_java_guidance/guides.py) *(Boot 3.0+)*：`.csrf().disable()` → `.csrf(AbstractHttpConfigurer::disable)`。
* [`BOOT-007`](./src/modern_java_guidance/guides.py) *(Boot 3.0+, 指南)*：在 `@RestControllerAdvice` 中返回 RFC 9457 `ProblemDetail`。

</details>

### Safe Adoption of Modern Features

* **版本门控执行**：仅当检测到的 Java/Spring Boot 版本满足规则最低要求（`min_java`、`min_boot`）时才激活对应规则。
* **注释感知扫描**：扫描前自动剥离 `//` 与 `/* ... */` 注释，避免注释文字引发误报。
* **注意事项（Caveats）**：每次通过 `mjg retrieve <ID>` 检索指南时，均附带实战注意事项（例如 JPA `@Entity` 不应使用 `record`）。

---

## How It Works

1. **Activation**：编程助手在 Java/Spring Boot 任务中激活 `modern-java-guidance` Skill（`4.1 KB`）。
2. **Version Detection**：运行 `mjg detect .` 解析 `pom.xml`、`build.gradle(.kts)`、`gradle/libs.versions.toml` 或 `.java-version`。
3. **On-Demand Guide Fetch**：通过 `mjg search "<topic>"` 与 `mjg retrieve <ID>` 按需拉取精确的前后对比代码与注意事项。
4. **Post-Edit Hook (`PostToolUse`)**：每次编辑 `.java` 后由 `mjg hook` 在 ~31 ms 内自动扫描并拦截或告警。

> [!TIP]
> `mjg` CLI 仅依赖 Python 3.11+ 标准库，**100% 离线、本地运行**，无需网络请求、API Key 或第三方供应链依赖。

---

## Alternative Installation Methods

* **Vercel Skills CLI (`npx skills`)**：`npx skills add wkd09/modern-java-guidance`
* **GitHub CLI**：`gh skill install wkd09/modern-java-guidance`
* **Google Antigravity**：`mjg setup --target antigravity --dir .`
* **Claude Code**：`mjg setup --target claude --dir .`
* **uv / pip（仅 CLI）**：
  ```bash
  uv tool install git+https://github.com/wkd09/modern-java-guidance.git
  # 或: pip install git+https://github.com/wkd09/modern-java-guidance.git
  ```

---

## Evals to prove this works well

参照 `GoogleChrome/modern-web-guidance` 的闭环验证流程，我们在 CI 中对每次提交自动运行基于断言的评估套件（[`scripts/eval_suite.py`](./scripts/eval_suite.py)）与性能基准（[`scripts/benchmark.py`](./scripts/benchmark.py)）：

```text
[ 专家编写的规则与指南 ]
        │
        ▼
[ 目标任务定义 ]       ──> 6 个 Java / Spring Boot 任务（无引导遗留基线 vs. 引导现代实现）
        │
        ▼
[ 校准与断言评分 ]     ──> 验证必备现代写法、禁用过时写法以及 `mjg check` 零告警
        │
        ▼
[ A/B 评估与性能基准 ] ──> 统计通过率提升、零误报率与单文件延迟
```

### Eval & benchmark results snapshot

#### 1. A/B 任务通过率（`python3 scripts/eval_suite.py`）

| 任务 | 目标环境 | 无引导基线 | 引导 + `mjg` Hook |
| :--- | :--- | :--- | :--- |
| `EVAL-01` Spring Security 6 配置 | Java 21, Boot 3.3.4 | FAIL（检出 3 处） | **PASS**（0 告警） |
| `EVAL-02` 同步 HTTP 客户端 | Java 21, Boot 3.3.4 | FAIL（检出 3 处） | **PASS**（0 告警） |
| `EVAL-03` Jakarta EE 持久层与校验 | Java 21, Boot 3.3.4 | FAIL（检出 2 处） | **PASS**（0 告警） |
| `EVAL-04` 阻塞 I/O 并发 | Java 21, Boot 3.3.4 | FAIL（检出 1 处） | **PASS**（0 告警） |
| `EVAL-05` SequencedCollection & `java.time` | Java 21, Boot 3.3.4 | FAIL（检出 2 处） | **PASS**（0 告警） |
| `EVAL-06` 旧版本兼容性保护 | Java 8, Boot 2.7.18 | PASS（零误报） | **PASS**（零误报） |
| **整体通过率 (Pass Rate)** | **6 个任务** | **16.7% (1/6)** | **100.0% (6/6, +83.3 pp)** |

#### 2. 与现有 Java / Spring Boot Skill 对比

| Skill / 仓库 | 初始 `SKILL.md` 体积 | 可执行 CLI | 版本自动检测 | `PostToolUse` Hook | 无 IDE/MCP 依赖 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`modern-java-guidance` (`mjg`)** | **4,157 bytes** | ✅ `mjg check` / `search` / `retrieve` | ✅ `pom.xml` / Gradle | ✅ Antigravity & Claude | ✅ 仅 Python 标准库 |
| **`github/awesome-copilot`** (`java-springboot` + `spring-security`) | 9,737 bytes | ❌ 仅 Markdown | ⚠️ 手动读取 | ❌ 无 | ✅ |
| **`Amplicode/spring-skills`** (`spring-security-configuration`) | 17,344 bytes | ❌ 无 | ⚠️ 依赖 IntelliJ MCP | ❌ 无 | ❌ 依赖 IntelliJ MCP |
| **`Santoshrt999/Java-Claude-Skills`** (`java-modernization-review`) | 20,103 bytes | ❌ 仅 Markdown | ❌ 无 | ❌ 无 | ✅ |

> 在 `Santoshrt999/Java-Claude-Skills/examples` 实测：`mjg` 自动从 `pom.xml` 检测到 Java 21，并立即检出 `TradeProcessor.java:15` 的 `Executors.newFixedThreadPool(10)`（`[JAVA-010]`）。

#### 3. 吞吐量与延迟（`python3 scripts/benchmark.py`，Apple Silicon）

| 测试项 | 规模 / 条件 | 实测结果 |
| :--- | :--- | :--- |
| **仓库扫描**（`detect` + `scan_target`） | 10 / 100 / 500 / 1,000 个 Java 文件 | **3.10 ms** / **22.84 ms** / **105.24 ms** / **183.40 ms**（`0.183 ms/file`） |
| **构建文件解析** | `pom.xml` / `build.gradle.kts` / `.java-version` | **0.059 ms** / **0.043 ms** / **0.045 ms** |
| **`PostToolUse` Hook（进程内）** | 单个 `.java` 文件（50 次） | **p50 0.257 ms** · p95 0.317 ms · max 0.373 ms |
| **CLI 子进程端到端延迟（`mjg hook`）** | 完整进程启动（10 次） | **中位数 31.0 ms**（30.5–86.3 ms） |

---

## Contributors & License

欢迎通过 [GitHub Issues](https://github.com/wkd09/modern-java-guidance/issues) 或 Pull Request 反馈问题与新增规则。

基于 [MIT License](./LICENSE) 开源。
