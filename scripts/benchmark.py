#!/usr/bin/env python3
"""Performance and accuracy benchmark for modern-java-guidance (mjg)."""

from __future__ import annotations

import json
import statistics
import tempfile
import time
from pathlib import Path

from modern_java_guidance.detector import detect_project
from modern_java_guidance.hook import run_hook
from modern_java_guidance.scanner import scan_target

LEGACY_FILE_TEMPLATE = """\
package com.example.service{idx};

import javax.persistence.Entity;
import javax.validation.constraints.NotNull;
import java.util.Collections;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.concurrent.Executors;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.client.RestTemplate;

// Legacy comments should not trigger: new Date(), RestTemplate, WebSecurityConfigurerAdapter
/* Multi-line comment:
   import javax.persistence.Id;
   .csrf().disable()
*/
@Entity
public class LegacyService{idx} extends WebSecurityConfigurerAdapter {{
    @Autowired
    private RestTemplate restTemplate;

    private final List<String> tags = Collections.unmodifiableList(Arrays.asList("a", "b"));

    public String process(List<String> items) {{
        var now = new Date();
        var last = items.get(items.size() - 1);
        var pool = Executors.newFixedThreadPool(4);
        var msg = String.format("Last=%s at %s", last, now);
        return msg + tags.size() + pool.toString();
    }}

    protected void configure(HttpSecurity http) throws Exception {{
        http.csrf().disable().authorizeRequests().antMatchers("/api/**").permitAll();
    }}
}}
"""

MODERN_FILE_TEMPLATE = """\
package com.example.modern{idx};

import jakarta.persistence.Entity;
import jakarta.validation.constraints.NotNull;
import java.time.Instant;
import java.util.List;
import java.util.concurrent.Executors;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
public class ModernService{idx} {{
    private final RestClient restClient;
    private final List<String> tags = List.of("a", "b");

    public ModernService{idx}(RestClient.Builder builder) {{
        this.restClient = builder.baseUrl("https://api.example.com").build();
    }}

    public String process(List<String> items) {{
        var now = Instant.now();
        var last = items.getLast();
        try (var pool = Executors.newVirtualThreadPerTaskExecutor()) {{
            return "Last=%s at %s (%d)".formatted(last, now, tags.size());
        }}
    }}
}}
"""

POM_BOOT3_JAVA21 = """\
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.4</version>
  </parent>
  <properties><java.version>21</java.version></properties>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-security</artifactId>
    </dependency>
  </dependencies>
</project>
"""


def bench_project_scan(num_files: int) -> tuple[float, int]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "pom.xml").write_text(POM_BOOT3_JAVA21, encoding="utf-8")
        src = root / "src" / "main" / "java" / "com" / "example"
        src.mkdir(parents=True)

        for i in range(num_files):
            template = LEGACY_FILE_TEMPLATE if i % 2 == 0 else MODERN_FILE_TEMPLATE
            (src / f"Service{i}.java").write_text(template.format(idx=i), encoding="utf-8")

        t0 = time.perf_counter()
        profile = detect_project(root)
        findings = scan_target(root, profile)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return elapsed_ms, len(findings)


def bench_post_tool_hook(iterations: int = 50) -> list[float]:
    latencies_ms: list[float] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "pom.xml").write_text(POM_BOOT3_JAVA21, encoding="utf-8")
        target = root / "TargetService.java"
        target.write_text(LEGACY_FILE_TEMPLATE.format(idx=0), encoding="utf-8")

        payload = json.dumps(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(target)},
            }
        )

        for _ in range(iterations):
            t0 = time.perf_counter()
            code, out, _ = run_hook("claude", payload)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            assert code == 0 and '"decision": "block"' in out
            latencies_ms.append(elapsed_ms)

    return latencies_ms


def bench_accuracy() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "pom.xml").write_text(POM_BOOT3_JAVA21, encoding="utf-8")
        legacy_file = root / "Legacy.java"
        modern_file = root / "Modern.java"
        legacy_file.write_text(LEGACY_FILE_TEMPLATE.format(idx=1), encoding="utf-8")
        modern_file.write_text(MODERN_FILE_TEMPLATE.format(idx=1), encoding="utf-8")

        profile = detect_project(root)
        legacy_findings = scan_target(legacy_file, profile)
        modern_findings = scan_target(modern_file, profile)

        # Legacy file has 11 distinct rule hits (JAVA-001, 002, 003, 010, 011 + BOOT-001..006)
        # Note: BOOT-001 matches 2 javax.* import lines
        expected_rules = {
            "JAVA-001",
            "JAVA-002",
            "JAVA-003",
            "JAVA-010",
            "JAVA-011",
            "BOOT-001",
            "BOOT-002",
            "BOOT-003",
            "BOOT-004",
            "BOOT-005",
            "BOOT-006",
        }
        detected_rules = {f.rule_id for f in legacy_findings}
        return {
            "expected_rule_count": len(expected_rules),
            "detected_rule_count": len(detected_rules),
            "missing_rules": sorted(expected_rules - detected_rules),
            "modern_false_positives": len(modern_findings),
        }


def main() -> None:
    print("=== 1. Project Scan Throughput (detect + scan_target) ===")
    for n in (10, 100, 500):
        runs = [bench_project_scan(n) for _ in range(3)]
        times = [r[0] for r in runs]
        findings_count = runs[0][1]
        med = statistics.median(times)
        per_file = med / n
        print(f"  {n:>3} Java files: median {med:6.2f} ms ({per_file:.3f} ms/file) | {findings_count} findings")

    print("\n=== 2. PostToolUse Hook Latency (50 runs, single edited file) ===")
    latencies = bench_post_tool_hook(50)
    latencies_sorted = sorted(latencies)
    p50 = statistics.median(latencies)
    p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
    p99 = latencies_sorted[-1]
    print(f"  p50: {p50:.3f} ms | p95: {p95:.3f} ms | max: {p99:.3f} ms")

    print("\n=== 3. Detection Accuracy (Java 21 + Spring Boot 3.3.4) ===")
    acc = bench_accuracy()
    print(f"  Legacy rules detected : {acc['detected_rule_count']}/{acc['expected_rule_count']} (missing: {acc['missing_rules']})")
    print(f"  Modern false positives: {acc['modern_false_positives']}")


if __name__ == "__main__":
    main()
