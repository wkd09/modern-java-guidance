"""Tests for modern-java-guidance detector, scanner, exporters, CLI, setup, and PostToolUse hooks."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from modern_java_guidance.cli import main
from modern_java_guidance.detector import ProjectProfile, detect_project
from modern_java_guidance.exporters import export_semgrep_yaml, filter_semgrep_rules
from modern_java_guidance.hook import run_hook
from modern_java_guidance.scanner import scan_file, scan_target


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

    def test_detect_gradle_java8_version_1_8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "build.gradle").write_text(
                "sourceCompatibility = JavaVersion.VERSION_1_8\n",
                encoding="utf-8",
            )
            profile = detect_project(root)
            self.assertEqual(profile.java_version, 8)
            self.assertEqual(profile.effective_java, 8)

    def test_detect_multimodule_maven_and_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            child = root / "service-a"
            child.mkdir()
            (root / "pom.xml").write_text(
                """\
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <properties>
    <java.version>21</java.version>
    <sb.ver>3.4.1</sb.ver>
  </properties>
  <dependencyManagement>
    <dependencies>
      <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-dependencies</artifactId>
        <version>${sb.ver}</version>
        <type>pom</type>
        <scope>import</scope>
      </dependency>
    </dependencies>
  </dependencyManagement>
</project>
""",
                encoding="utf-8",
            )
            (child / "pom.xml").write_text(
                """\
<project>
  <parent>
    <groupId>com.acme</groupId>
    <artifactId>root</artifactId>
    <version>1.0.0</version>
  </parent>
  <artifactId>service-a</artifactId>
</project>
""",
                encoding="utf-8",
            )
            profile = detect_project(child)
            self.assertEqual(profile.java_version, 21)
            self.assertEqual(profile.spring_boot_version, (3, 4, 1))

    def test_detect_multimodule_gradle_version_catalog_camelcase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "gradle").mkdir()
            (root / "gradle" / "libs.versions.toml").write_text(
                '[versions]\njavaVersion = "21"\nspringBoot = "3.4.0"\n',
                encoding="utf-8",
            )
            sub = root / "api-module"
            sub.mkdir()
            (sub / "build.gradle.kts").write_text('plugins { alias(libs.plugins.spring.boot) }\n', encoding="utf-8")
            profile = detect_project(sub)
            self.assertEqual(profile.java_version, 21)
            self.assertEqual(profile.spring_boot_version, (3, 4, 0))

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

            # Verify caught_by_javac metadata accurately distinguishes silent vs compiler-caught rules
            javac_map = {f.rule_id: f.caught_by_javac for f in findings_modern}
            self.assertEqual(javac_map["JAVA-001"], "no")
            self.assertEqual(javac_map["JAVA-010"], "no")
            self.assertEqual(javac_map["BOOT-003"], "no")
            self.assertEqual(javac_map["BOOT-004"], "no")
            self.assertEqual(javac_map["BOOT-001"], "compile-error")
            self.assertEqual(javac_map["BOOT-002"], "compile-error")
            self.assertEqual(javac_map["BOOT-005"], "compile-error")
            self.assertEqual(javac_map["BOOT-006"], "deprecated")
            self.assertIn("caught_by_javac", findings_modern[0].to_dict())

    def test_scanner_edge_cases_and_suppression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_main = root / "src" / "main" / "java"
            src_test = root / "src" / "test" / "java"
            src_main.mkdir(parents=True)
            src_test.mkdir(parents=True)
            profile = ProjectProfile(java_version=21, spring_boot_version=(3, 4, 0), source_file=None)

            edge = src_main / "EdgeCases.java"
            edge.write_text(
                '''\
package com.example;

import javax.inject.Inject;
import java.util.Calendar;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.Executors;
import java.util.stream.Collectors;

public class EdgeCases {
    // Constructor @Autowired is NOT field injection -> must NOT trigger BOOT-004
    @Autowired
    public EdgeCases(String dep) {}

    // Inline field injection -> MUST trigger BOOT-004
    @Autowired private String inlineField;

    // String literals, escaped backslash quotes, and text blocks must NOT trigger false positives
    String msg = "Avoid new Date() and RestTemplate \\\\";
    String block = """
        new Date()
        RestTemplate
        http.csrf().disable()
        """;

    // Explicit Locale in String.format -> must NOT trigger JAVA-003
    String localized = String.format(Locale.US, "Hi %s", "Bob");

    // Inline suppression works on same line and preceding line
    void suppressed() {
        var cpuPool = Executors.newFixedThreadPool(4); // mjg:ignore JAVA-010
        // mjg:ignore JAVA-001
        var legacyCal = Calendar.getInstance();
    }

    // Active new rules: JAVA-001 Calendar, JAVA-004 Collectors.toList, multiline BOOT-006
    List<String> active(List<String> xs, Object http) {
        var cal = Calendar.getInstance();
        http
            .csrf()
            .disable();
        return xs.stream().collect(Collectors.toList());
    }
}
''',
                encoding="utf-8",
            )
            findings = scan_file(edge, profile)
            by_rule = {f.rule_id: [x.line for x in findings if x.rule_id == f.rule_id] for f in findings}
            self.assertEqual(set(by_rule.keys()), {"BOOT-001", "BOOT-004", "JAVA-001", "BOOT-006", "JAVA-004"})
            self.assertEqual(by_rule["BOOT-004"], [16])
            self.assertEqual(by_rule["JAVA-001"], [38])
            self.assertEqual(by_rule["BOOT-006"], [40])
            self.assertEqual(by_rule["JAVA-004"], [42])

            # Test file: @Autowired is skipped, while @MockBean triggers BOOT-008 on Boot 3.4+
            test_java = src_test / "OrderServiceTest.java"
            test_java.write_text(
                """\
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.MockBean;
class OrderServiceTest {
    @Autowired
    private Object svc;
    @MockBean
    private Object gateway;
}
""",
                encoding="utf-8",
            )
            test_findings = scan_file(test_java, profile)
            test_rule_ids = {f.rule_id for f in test_findings}
            self.assertNotIn("BOOT-004", test_rule_ids)
            self.assertIn("BOOT-008", test_rule_ids)

            # Boot 3.3 must NOT trigger BOOT-008 (@MockitoBean introduced in Boot 3.4)
            profile_33 = ProjectProfile(java_version=21, spring_boot_version=(3, 3, 4), source_file=None)
            self.assertEqual(scan_file(test_java, profile_33), [])

    def test_config_scanners_sleuth_and_dockerfile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pom.xml").write_text(
                """\
<project>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.4</version>
  </parent>
  <dependencies>
    <dependency>
      <groupId>org.springframework.cloud</groupId>
      <artifactId>spring-cloud-starter-sleuth</artifactId>
    </dependency>
  </dependencies>
</project>
""",
                encoding="utf-8",
            )
            (root / "Dockerfile").write_text(
                'FROM eclipse-temurin:21-jre\nCOPY target/app.jar /app.jar\nENTRYPOINT ["java", "-jar", "/app.jar"]\n',
                encoding="utf-8",
            )
            profile = detect_project(root)
            findings = scan_target(root, profile)
            rule_ids = {f.rule_id for f in findings}
            self.assertEqual(rule_ids, {"BOOT-009", "BOOT-010"})

            # Extracted layout Dockerfile -> no BOOT-010
            (root / "Dockerfile").write_text(
                'FROM eclipse-temurin:21-jre\nRUN java -Djarmode=tools -jar app.jar extract\nENTRYPOINT ["java", "-jar", "/app/app.jar"]\n',
                encoding="utf-8",
            )
            findings2 = scan_target(root, profile)
            self.assertEqual({f.rule_id for f in findings2}, {"BOOT-009"})

    def test_hook_antigravity_and_claude_error_vs_advisory(self) -> None:
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
            err_file = root / "Err.java"
            err_file.write_text("import javax.persistence.Entity;\n", encoding="utf-8")

            agy_payload = json.dumps(
                {
                    "toolCall": {
                        "name": "write_file",
                        "args": {"Path": str(err_file)},
                    }
                }
            )
            code, out, err = run_hook("antigravity", agy_payload)
            self.assertEqual(code, 0)
            self.assertEqual(out, "{}")
            self.assertIn("BOOT-001", err)

            # Error severity -> Claude blocks
            claude_err = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(err_file)}})
            code, out, err = run_hook("claude", claude_err)
            self.assertEqual(code, 0)
            parsed = json.loads(out)
            self.assertEqual(parsed["decision"], "block")
            self.assertIn("BOOT-001", parsed["reason"])

            # Warning/info-only -> Claude gets non-blocking additionalContext by default
            info_file = root / "Info.java"
            info_file.write_text('class Info { String s = String.format("Hi %s", "x"); }\n', encoding="utf-8")
            claude_info = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(info_file)}})
            code, out, err = run_hook("claude", claude_info)
            self.assertEqual(code, 0)
            parsed_info = json.loads(out)
            self.assertNotIn("decision", parsed_info)
            self.assertIn("JAVA-003", parsed_info["hookSpecificOutput"]["additionalContext"])

            # Strict mode -> blocks even on info/warning
            code, out_strict, _ = run_hook("claude", claude_info, strict=True)
            self.assertEqual(json.loads(out_strict)["decision"], "block")

    def test_cli_detect_check_setup_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "build.gradle.kts").write_text(
                'java { toolchain { languageVersion.set(JavaLanguageVersion.of(21)) } }\n',
                encoding="utf-8",
            )
            (root / "Good.java").write_text("import java.time.Instant;\npublic record Good(Instant ts) {}\n", encoding="utf-8")
            self.assertEqual(main(["detect", str(root)]), 0)
            self.assertEqual(main(["check", str(root), "--strict"]), 0)
            # Invalid --boot returns exit code 2
            self.assertEqual(main(["check", str(root), "--boot", "invalid"]), 2)
            self.assertEqual(main(["export", "--format", "semgrep", "--boot", "invalid"]), 2)

            # Setup installs both skills and hooks for antigravity & claude
            skill_dest = root / "agy-skill"
            self.assertEqual(main(["setup", "--target", "all", "--dir", str(root), "--skill-dir", str(skill_dest)]), 0)
            self.assertTrue((skill_dest / "SKILL.md").is_file())
            self.assertTrue((root / ".claude" / "skills" / "modern-java-guidance" / "SKILL.md").is_file())
            hooks_json = json.loads((root / ".agents" / "hooks.json").read_text(encoding="utf-8"))
            matcher = hooks_json["modern-java-guidance"]["PostToolUse"][0]["matcher"]
            self.assertIn("write_file", matcher)
            self.assertIn("edit_file", matcher)

    def test_cli_search_and_retrieve(self) -> None:
        self.assertEqual(main(["search", "security"]), 0)
        self.assertEqual(main(["retrieve", "BOOT-002"]), 0)
        self.assertEqual(main(["retrieve", "BOOT-008"]), 0)
        self.assertEqual(main(["retrieve", "BOOT-009"]), 0)
        self.assertEqual(main(["retrieve", "BOOT-010"]), 0)
        self.assertEqual(main(["retrieve", "NONEXISTENT-999"]), 1)

    def test_semgrep_export_version_gating_and_sync(self) -> None:
        # Java 8 + Boot 2.7 -> no modern rules exported
        legacy_profile = ProjectProfile(java_version=8, spring_boot_version=(2, 7, 18), source_file=None)
        self.assertEqual(filter_semgrep_rules(legacy_profile), [])
        self.assertIn("rules: []", export_semgrep_yaml(legacy_profile))

        # Java 21 + Boot 3.1 -> omits BOOT-003 (3.2+) and BOOT-008 (3.4+)
        boot31_profile = ProjectProfile(java_version=21, spring_boot_version=(3, 1, 5), source_file=None)
        boot31_ids = {spec.rule_id for spec in filter_semgrep_rules(boot31_profile)}
        self.assertNotIn("BOOT-003", boot31_ids)
        self.assertNotIn("BOOT-008", boot31_ids)
        self.assertIn("BOOT-001", boot31_ids)
        self.assertIn("JAVA-004", boot31_ids)
        self.assertIn("JAVA-010", boot31_ids)

        # Java 21 + Boot 3.4 -> all 13 Java rules exported, matching committed ruleset
        boot34_profile = ProjectProfile(java_version=21, spring_boot_version=(3, 4, 0), source_file=None)
        exported = export_semgrep_yaml(boot34_profile)
        self.assertEqual(len(filter_semgrep_rules(boot34_profile)), 13)
        committed_yaml = Path(__file__).resolve().parent.parent / "rules" / "semgrep" / "modern-java-boot3.yaml"
        self.assertEqual(exported, committed_yaml.read_text(encoding="utf-8"))

        # CLI export writes valid output file
        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "custom.yaml"
            rc = main(["export", "--format", "semgrep", "--java", "21", "--boot", "3.4.0", "-o", str(out_file)])
            self.assertEqual(rc, 0)
            self.assertEqual(out_file.read_text(encoding="utf-8"), exported)


if __name__ == "__main__":
    unittest.main()
