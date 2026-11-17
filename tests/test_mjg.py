"""Tests for modern-java-guidance detector, scanner, CLI, and PostToolUse hooks."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from modern_java_guidance.cli import main
from modern_java_guidance.detector import detect_project
from modern_java_guidance.hook import run_hook
from modern_java_guidance.scanner import scan_file


LEGACY_BOOT3_SAMPLE = """\
package com.example.demo;

import javax.persistence.Entity;
import java.util.Date;
import java.util.List;
import java.util.concurrent.Executors;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.client.RestTemplate;

// Commented out new Date() should be ignored!
public class LegacyService extends WebSecurityConfigurerAdapter {
    @Autowired
    private RestTemplate restTemplate;

    public void run(List<String> items) {
        var now = new Date();
        var last = items.get(items.size() - 1);
        var pool = Executors.newFixedThreadPool(8);
        var client = new RestTemplate();
    }

    protected void configure(HttpSecurity http) throws Exception {
        http.csrf().disable().authorizeRequests().antMatchers("/public/**").permitAll();
    }
}
"""


class ModernJavaGuidanceTests(unittest.TestCase):
    def test_detect_maven_java21_boot33(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pom.xml").write_text(
                """\
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.4</version>
  </parent>
  <properties>
    <java.version>21</java.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-security</artifactId>
    </dependency>
  </dependencies>
</project>
""",
                encoding="utf-8",
            )
            profile = detect_project(root)
            self.assertEqual(profile.java_version, 21)
            self.assertEqual(profile.spring_boot_version, (3, 3, 4))
            self.assertTrue(profile.uses_spring_security)

    def test_detect_gradle_kts_java17_boot27(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "build.gradle.kts").write_text(
                """\
plugins {
    id("org.springframework.boot") version "2.7.18"
}
java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(17))
    }
}
""",
                encoding="utf-8",
            )
            profile = detect_project(root)
            self.assertEqual(profile.java_version, 17)
            self.assertEqual(profile.spring_boot_version, (2, 7, 18))

    def test_scanner_respects_version_gating(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            java_file = root / "LegacyService.java"
            java_file.write_text(LEGACY_BOOT3_SAMPLE, encoding="utf-8")

            # 1. Under Java 8 + Boot 2.7 -> Java 21 & Boot 3 rules must NOT fire
            (root / "pom.xml").write_text(
                """\
<project>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>2.7.18</version>
  </parent>
  <properties><java.version>1.8</java.version></properties>
</project>
""",
                encoding="utf-8",
            )
            profile_legacy = detect_project(java_file)
            findings_legacy = scan_file(java_file, profile_legacy)
            self.assertEqual(findings_legacy, [])

            # 2. Under Java 21 + Boot 3.3 -> All applicable rules fire (and comment line is ignored)
            (root / "pom.xml").write_text(
                """\
<project>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.4</version>
  </parent>
  <properties><java.version>21</java.version></properties>
</project>
""",
                encoding="utf-8",
            )
            profile_modern = detect_project(java_file)
            findings_modern = scan_file(java_file, profile_modern)
            rule_ids = {f.rule_id for f in findings_modern}
            self.assertEqual(
                rule_ids,
                {
                    "JAVA-001",
                    "JAVA-010",
                    "JAVA-011",
                    "BOOT-001",
                    "BOOT-002",
                    "BOOT-003",
                    "BOOT-004",
                    "BOOT-005",
                    "BOOT-006",
                },
            )
            # Ensure commented `new Date()` on line 10 was NOT flagged
            date_lines = [f.line for f in findings_modern if f.rule_id == "JAVA-001"]
            self.assertEqual(date_lines, [16])

    def test_hook_antigravity_and_claude_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pom.xml").write_text(
                """\
<project>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.0</version>
  </parent>
  <properties><java.version>21</java.version></properties>
</project>
""",
                encoding="utf-8",
            )
            java_file = root / "App.java"
            java_file.write_text("import javax.persistence.Entity;\n", encoding="utf-8")

            agy_payload = json.dumps(
                {
                    "toolCall": {
                        "name": "write_to_file",
                        "args": {"TargetFile": str(java_file)},
                    }
                }
            )
            code, out, err = run_hook("antigravity", agy_payload)
            self.assertEqual(code, 0)
            self.assertEqual(out, "{}")
            self.assertIn("BOOT-001", err)

            claude_payload = json.dumps(
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": str(java_file)},
                }
            )
            code, out, err = run_hook("claude", claude_payload)
            self.assertEqual(code, 0)
            parsed = json.loads(out)
            self.assertEqual(parsed["decision"], "block")
            self.assertIn("BOOT-001", parsed["reason"])

    def test_cli_detect_and_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "build.gradle.kts").write_text('java { toolchain { languageVersion.set(JavaLanguageVersion.of(21)) } }\n', encoding="utf-8")
            (root / "Good.java").write_text("import java.time.Instant;\npublic record Good(Instant ts) {}\n", encoding="utf-8")
            self.assertEqual(main(["detect", str(root)]), 0)
            self.assertEqual(main(["check", str(root), "--strict"]), 0)


if __name__ == "__main__":
    unittest.main()
