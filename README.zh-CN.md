<div align="center">

<img src="./assets/logo.svg" width="88" height="88" alt="modern-java-guidance logo" />

# Modern Java Guidance (`mjg`)

**Modern Java Guidance** 是一套将 **Java 17/21/25+** 与 **Spring Boot 3.x+** 最佳实践直接嵌入 AI 编程助手的版本感知 CLI 扫描器、`PostToolUse` Hook 与 Agent Skill。

[![CI](https://github.com/wkd09/modern-java-guidance/actions/workflows/ci.yml/badge.svg)](https://github.com/wkd09/modern-java-guidance/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](./pyproject.toml)
[![Dependencies: Zero](https://img.shields.io/badge/dependencies-zero-success.svg)](./pyproject.toml)

[English](./README.md) | [한국어](./README.ko.md) | [简体中文](./README.zh-CN.md)

</div>

---

## 为什么需要 Modern Java Guidance？

由于 LLM 训练数据中充斥着大量 **Java 8 与 Spring Boot 2.x** 时期的遗留代码，即使在全新的 Java 21 + Spring Boot 3.x 项目中，未经引导的模型也经常输出已被移除的 `javax.*` 导入、`WebSecurityConfigurerAdapter`、`RestTemplate` 或 `Executors.newFixedThreadPool()`。

即使模型知道新 API 的存在，单纯的静态 Markdown 提示词也无法阻止长对话中的习惯性回退。Modern Java Guidance 通过可执行 CLI 与 `PostToolUse` 护栏弥合了这一差距：

* **版本感知自动检测（`mjg detect`）**：解析 `pom.xml`、`build.gradle(.kts)`、`gradle/libs.versions.toml` 与 `.java-version`，确保 Java 8 / Boot 2.x 老项目不会出现误报。
* **按需检索模式指南（`mjg search` / `mjg retrieve`）**：将 `SKILL.md` 控制在仅 **4.1 KB**，需要时再按 ID 或关键字精确调取 Before/After 示例。
* **确定性编辑后护栏（`mjg hook`）**：每次修改 `.java` 文件后仅需 **~31 ms**（零 LLM Token）自动扫描并拦截过时写法。

---

## 快速开始

一条命令安装 `mjg`（需要 Python 3.11+，零第三方依赖）：

```bash
curl -fsSL https://raw.githubusercontent.com/wkd09/modern-java-guidance/main/install.sh | bash
```

在你的 Java / Spring Boot 项目中配置 Skill 与 `PostToolUse` Hook：

```bash
mjg setup --target all --dir /path/to/your/spring-boot-project
```

### 免安装直接体验（`uvx`）

```bash
# 自动识别 pom.xml / build.gradle(.kts) 版本并扫描项目
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg check .

# 按关键字搜索现代写法指南
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg search "security"

# 按 ID 获取详细前后对比示例
uvx --from git+https://github.com/wkd09/modern-java-guidance.git mjg retrieve BOOT-002
```

---

## 与编程 Agent 集成

* **Vercel Agent Skills（Claude Code、Cursor、Copilot、Codex、Antigravity）**：
  ```bash
  npx skills add wkd09/modern-java-guidance
  ```
* **Antigravity（`PostToolUse` Hook + 全局 Skill）**：
  ```bash
  mjg setup --target antigravity --dir .
  ```
* **Claude Code（返回 `"decision": "block"` 的 `PostToolUse` Hook）**：
  ```bash
  mjg setup --target claude --dir .
  ```

<details>
<summary>生成的 Hook 配置示例（<code>.claude/settings.json</code> / <code>.agents/hooks.json</code>）</summary>

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

## 包含内容

* **Java 17 / 21 / 25+ 语言与标准库**：`record`、`sealed interface`、`switch` 模式匹配、`SequencedCollection`（`getFirst()`、`getLast()`）、虚拟线程（`Executors.newVirtualThreadPerTaskExecutor()`）、`java.time`、不可变集合工厂（`List.of`、`Map.of`）与 `String.formatted()`。
* **Spring Boot 3.x+ & Spring Security 6**：`jakarta.*`（Jakarta EE 10）迁移、`SecurityFilterChain` Lambda DSL（`authorizeHttpRequests`、`requestMatchers`、`AbstractHttpConfigurer::disable`）、`RestClient` & `@HttpExchange`（Boot 3.2+）、构造函数注入以及 RFC 9457 `ProblemDetail`。
* **旧版本兼容性保护**：当 `pom.xml` 或 `build.gradle(.kts)` 目标为 Java 8/11 或 Boot 2.x 时，自动跳过 Java 21 与 Boot 3+ 规则。

<details>
<summary>完整版本门控规则目录（11 条可执行扫描规则 + 13 篇按需指南）</summary>

| 规则 ID | 级别 | 生效版本 | 检测的过时写法 | 推荐现代写法 |
| :--- | :--- | :--- | :--- | :--- |
| `JAVA-001` | `warning` | Java 16+ | `new Date()`, `SimpleDateFormat` | `java.time` (`Instant`, `LocalDate`, `DateTimeFormatter`) |
| `JAVA-002` | `warning` | Java 16+ | `Collections.unmodifiableList(Arrays.asList(...))` | `List.of(...)`, `Set.of(...)`, `Map.of(...)` |
| `JAVA-003` | `info` | Java 16+ | `String.format(...)` | `"..." .formatted(...)` |
| `JAVA-010` | `warning` | Java 21+ | `Executors.newFixedThreadPool` / `newCachedThreadPool` | `Executors.newVirtualThreadPerTaskExecutor()`（I/O 密集型） |
| `JAVA-011` | `warning` | Java 21+ | `list.get(list.size() - 1)` | `SequencedCollection.getLast()` |
| `BOOT-001` | `error` | Boot 3.0+ | `import javax.{persistence,validation,servlet,...}.*` | `import jakarta.*` |
| `BOOT-002` | `error` | Boot 3.0+ | `extends WebSecurityConfigurerAdapter` | `@Bean SecurityFilterChain` |
| `BOOT-003` | `warning` | Boot 3.2+ | `RestTemplate` / `RestTemplateBuilder` | `RestClient` / `@HttpExchange` |
| `BOOT-004` | `warning` | Boot 3.0+ | `@Autowired` 字段注入 | 构造函数注入 |
| `BOOT-005` | `error` | Boot 3.0+ | `.antMatchers()` / `.mvcMatchers()` / `.authorizeRequests()` | `.authorizeHttpRequests(a -> a.requestMatchers(...))` |
| `BOOT-006` | `error` | Boot 3.0+ | `.csrf().disable()` | `.csrf(AbstractHttpConfigurer::disable)` |

</details>

---

## 评估与性能基准

### 1. 基于断言的 A/B 评估（`scripts/eval_suite.py`）

参考 `GoogleChrome/modern-web-guidance` 的断言评分方法，`scripts/eval_suite.py` 在**无引导遗留基线（Unguided）**与**引导 + `mjg` Hook（Guided）**两种条件下对 **6 个典型 Java / Spring Boot 任务**进行对比评估：

| 指标 | 无引导遗留基线 | 引导 + `mjg` Hook | 提升幅度 (Uplift) |
| :--- | :--- | :--- | :--- |
| **整体任务通过率 (Pass Rate)** | **1 / 6 (16.7%)** | **6 / 6 (100.0%)** | **+83.3 个百分点** |

| 任务 | 目标环境 | 无引导基线 | 引导 + `mjg` Hook |
| :--- | :--- | :--- | :--- |
| `EVAL-01` Spring Security 6 配置 | Java 21, Boot 3.3.4 | FAIL（检出 3 处 `mjg` 告警） | **PASS**（0 告警） |
| `EVAL-02` 同步 HTTP 客户端 | Java 21, Boot 3.3.4 | FAIL（检出 3 处 `mjg` 告警） | **PASS**（0 告警） |
| `EVAL-03` Jakarta EE 持久层与校验 | Java 21, Boot 3.3.4 | FAIL（检出 2 处 `mjg` 告警） | **PASS**（0 告警） |
| `EVAL-04` 阻塞 I/O 并发 | Java 21, Boot 3.3.4 | FAIL（检出 1 处 `mjg` 告警） | **PASS**（0 告警） |
| `EVAL-05` SequencedCollection & `java.time` | Java 21, Boot 3.3.4 | FAIL（检出 2 处 `mjg` 告警） | **PASS**（0 告警） |
| `EVAL-06` 旧版本兼容性保护 | Java 8, Boot 2.7.18 | PASS（零误报） | **PASS**（零误报） |

### 2. 与现有 Java / Spring Boot Skill 对比

| 对比维度 | **`modern-java-guidance` (`mjg`)** | **`github/awesome-copilot`**<br>(`java-springboot` + `spring-security`) | **`Amplicode/spring-skills`**<br>(`spring-security-configuration`) | **`Santoshrt999/Java-Claude-Skills`**<br>(`java-modernization-review`) |
| :--- | :--- | :--- | :--- | :--- |
| **初始 `SKILL.md` 体积** | **4,157 bytes** | 9,737 bytes (4,433 + 5,304) | 17,344 bytes (4.2×) | 20,103 bytes (4.8×) |
| **可执行 CLI 扫描器** | ✅ `mjg check`（零 LLM Token） | ❌ 仅 Markdown | ❌ 无 | ❌ 仅 Markdown |
| **版本自动检测** | ✅ `mjg detect` (`pom.xml` / Gradle) | ⚠️ 需手动读取 | ⚠️ 依赖 IntelliJ MCP | ❌ 无 |
| **`PostToolUse` 自动拦截** | ✅ Antigravity & Claude Code | ❌ 无 | ❌ 无 | ❌ 无 |
| **外部 / IDE 依赖** | **零依赖**（仅 Python 标准库） | 无 | ❌ 需 IntelliJ Amplicode MCP | 无 |

### 3. 吞吐量与延迟（`scripts/benchmark.py`）

Apple Silicon 实测（仅使用 Python 标准库）：

| 测试项 | 规模 / 条件 | 实测结果 |
| :--- | :--- | :--- |
| **仓库扫描**（`detect` + `scan_target`） | 10 / 100 / 500 / 1,000 个 Java 文件 | **3.10 ms** / **22.84 ms** / **105.24 ms** / **183.40 ms**（`0.183 ms/file`） |
| **构建文件解析** | `pom.xml` / `build.gradle.kts` / `.java-version` | **0.059 ms** / **0.043 ms** / **0.045 ms** |
| **`PostToolUse` Hook（进程内）** | 单个 `.java` 文件（50 次） | **p50 0.257 ms** · p95 0.317 ms · max 0.373 ms |
| **CLI 子进程端到端延迟（`mjg hook`）** | 完整进程启动（10 次） | **中位数 31.0 ms**（30.5–86.3 ms） |

---

## 开源协议

[MIT](./LICENSE)
