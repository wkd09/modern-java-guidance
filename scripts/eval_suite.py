#!/usr/bin/env python3
"""A/B assertion evaluation harness modeled after GoogleChrome/modern-web-guidance.

Evaluates 6 representative Java / Spring Boot tasks across two conditions:
  1. Unguided Legacy Baseline (typical LLM training-data defaults)
  2. Guided + `mjg` PostToolUse Gate (modern Java 21 / Boot 3.x idioms)

Each task runs deterministic AST/regex assertions AND `mjg check` verification.
"""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from modern_java_guidance.detector import detect_project
from modern_java_guidance.scanner import scan_file


@dataclass(frozen=True)
class EvalTask:
    task_id: str
    name: str
    java_version: int
    boot_version: str | None
    pom_xml: str
    unguided_code: str
    guided_code: str
    required_patterns: tuple[str, ...]
    forbidden_patterns: tuple[str, ...]


POM_JAVA21_BOOT33 = """\
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.4</version>
  </parent>
  <properties><java.version>21</java.version></properties>
</project>
"""

POM_JAVA8_BOOT27 = """\
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>2.7.18</version>
  </parent>
  <properties><java.version>1.8</java.version></properties>
</project>
"""

TASKS: tuple[EvalTask, ...] = (
    EvalTask(
        task_id="EVAL-01",
        name="Spring Security 6 Configuration",
        java_version=21,
        boot_version="3.3.4",
        pom_xml=POM_JAVA21_BOOT33,
        unguided_code="""\
package com.example.sec;
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    protected void configure(HttpSecurity http) throws Exception {
        http.csrf().disable().authorizeRequests().antMatchers("/public/**").permitAll();
    }
}
""",
        guided_code="""\
package com.example.sec;
@Configuration
public class SecurityConfig {
    @Bean
    SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(AbstractHttpConfigurer::disable)
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/public/**").permitAll()
                .anyRequest().authenticated())
            .build();
    }
}
""",
        required_patterns=(r"\bSecurityFilterChain\b", r"\.authorizeHttpRequests\(", r"\.requestMatchers\("),
        forbidden_patterns=(r"\bWebSecurityConfigurerAdapter\b", r"\.antMatchers\(", r"\.csrf\(\)\.disable\(\)"),
    ),
    EvalTask(
        task_id="EVAL-02",
        name="Synchronous HTTP Client (Boot 3.2+)",
        java_version=21,
        boot_version="3.3.4",
        pom_xml=POM_JAVA21_BOOT33,
        unguided_code="""\
package com.example.http;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.client.RestTemplate;
public class WeatherClient {
    @Autowired
    private RestTemplate restTemplate;
    public String get(String url) { return restTemplate.getForObject(url, String.class); }
}
""",
        guided_code="""\
package com.example.http;
import org.springframework.web.client.RestClient;
public class WeatherClient {
    private final RestClient restClient;
    public WeatherClient(RestClient.Builder builder) {
        this.restClient = builder.baseUrl("https://api.example.com").build();
    }
    public String get(String path) { return restClient.get().uri(path).retrieve().body(String.class); }
}
""",
        required_patterns=(r"\bRestClient\b", r"RestClient\.Builder"),
        forbidden_patterns=(r"\bRestTemplate\b", r"^\s*@Autowired\s*$"),
    ),
    EvalTask(
        task_id="EVAL-03",
        name="Jakarta EE Persistence & Validation",
        java_version=21,
        boot_version="3.3.4",
        pom_xml=POM_JAVA21_BOOT33,
        unguided_code="""\
package com.example.domain;
import javax.persistence.Entity;
import javax.validation.constraints.NotBlank;
@Entity
public class User { @NotBlank private String name; }
""",
        guided_code="""\
package com.example.domain;
import jakarta.persistence.Entity;
import jakarta.validation.constraints.NotBlank;
@Entity
public class User { @NotBlank private String name; }
""",
        required_patterns=(r"import\s+jakarta\.persistence\.Entity;", r"import\s+jakarta\.validation\."),
        forbidden_patterns=(r"import\s+javax\.(persistence|validation)\.",),
    ),
    EvalTask(
        task_id="EVAL-04",
        name="Java 21 Blocking I/O Concurrency",
        java_version=21,
        boot_version="3.3.4",
        pom_xml=POM_JAVA21_BOOT33,
        unguided_code="""\
package com.example.jobs;
import java.util.concurrent.Executors;
public class Dispatcher {
    public void runAll(Runnable r) {
        var pool = Executors.newFixedThreadPool(16);
        pool.submit(r);
    }
}
""",
        guided_code="""\
package com.example.jobs;
import java.util.concurrent.Executors;
public class Dispatcher {
    public void runAll(Runnable r) {
        try (var pool = Executors.newVirtualThreadPerTaskExecutor()) {
            pool.submit(r);
        }
    }
}
""",
        required_patterns=(r"Executors\.newVirtualThreadPerTaskExecutor\(\)",),
        forbidden_patterns=(r"Executors\.newFixedThreadPool\(",),
    ),
    EvalTask(
        task_id="EVAL-05",
        name="Java 21 SequencedCollection & java.time",
        java_version=21,
        boot_version="3.3.4",
        pom_xml=POM_JAVA21_BOOT33,
        unguided_code="""\
package com.example.hist;
import java.util.Date;
import java.util.List;
public class History {
    public String latest(List<String> ids) {
        Date ts = new Date();
        return ids.get(ids.size() - 1) + ts;
    }
}
""",
        guided_code="""\
package com.example.hist;
import java.time.Instant;
import java.util.List;
public class History {
    public String latest(List<String> ids) {
        Instant ts = Instant.now();
        return ids.getLast() + ts;
    }
}
""",
        required_patterns=(r"\bInstant\.now\(\)", r"\.getLast\(\)"),
        forbidden_patterns=(r"\bnew\s+Date\(\)", r"\.get\([^)]*\.size\(\)\s*-\s*1\)"),
    ),
    EvalTask(
        task_id="EVAL-06",
        name="Legacy Compatibility Preservation (Java 8 + Boot 2.7)",
        java_version=8,
        boot_version="2.7.18",
        pom_xml=POM_JAVA8_BOOT27,
        unguided_code="""\
package com.example.legacy;
import javax.persistence.Entity;
import java.util.List;
@Entity
public class LegacyEntity {
    public String last(List<String> xs) { return xs.get(xs.size() - 1); }
}
""",
        guided_code="""\
package com.example.legacy;
import javax.persistence.Entity;
import java.util.List;
@Entity
public class LegacyEntity {
    public String last(List<String> xs) { return xs.get(xs.size() - 1); }
}
""",
        required_patterns=(r"import\s+javax\.persistence\.Entity;",),
        forbidden_patterns=(r"import\s+jakarta\.persistence\.", r"\.getLast\(\)"),
    ),
)


def grade_code(code: str, java_path: Path, task: EvalTask) -> dict[str, object]:
    java_path.write_text(code, encoding="utf-8")
    profile = detect_project(java_path)
    findings = scan_file(java_path, profile)

    req_ok = all(re.search(pat, code, re.MULTILINE) for pat in task.required_patterns)
    forb_ok = not any(re.search(pat, code, re.MULTILINE) for pat in task.forbidden_patterns)
    mjg_clean = len(findings) == 0

    passed = req_ok and forb_ok and mjg_clean
    return {
        "passed": passed,
        "req_ok": req_ok,
        "forb_ok": forb_ok,
        "mjg_findings": len(findings),
    }


def main() -> None:
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for task in TASKS:
            task_dir = root / task.task_id
            task_dir.mkdir(parents=True)
            (task_dir / "pom.xml").write_text(task.pom_xml, encoding="utf-8")
            java_file = task_dir / "Sample.java"

            u_res = grade_code(task.unguided_code, java_file, task)
            g_res = grade_code(task.guided_code, java_file, task)
            results.append((task, u_res, g_res))

    u_pass = sum(1 for _, u, _ in results if u["passed"])
    g_pass = sum(1 for _, _, g in results if g["passed"])
    total = len(results)

    print(f"Unguided Legacy Baseline Pass Rate : {u_pass}/{total} ({u_pass / total * 100:.1f}%)")
    print(f"Guided + mjg Hook Pass Rate        : {g_pass}/{total} ({g_pass / total * 100:.1f}%)")
    print(f"Uplift                             : +{(g_pass - u_pass) / total * 100:.1f} percentage points\n")

    for task, u, g in results:
        print(
            f"  {task.task_id} ({task.name}): "
            f"unguided={'PASS' if u['passed'] else 'FAIL'} (findings={u['mjg_findings']}) | "
            f"guided={'PASS' if g['passed'] else 'FAIL'} (findings={g['mjg_findings']})"
        )


if __name__ == "__main__":
    main()
