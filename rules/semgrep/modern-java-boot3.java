package com.example.demo;

// ruleid: mjg-boot-001-javax-ee-import
import javax.persistence.Entity;
// ruleid: mjg-boot-001-javax-ee-import
import javax.validation.constraints.NotNull;
// ruleid: mjg-boot-001-javax-ee-import
import javax.inject.Inject;
// ok: mjg-boot-001-javax-ee-import
import jakarta.persistence.Table;

import java.text.SimpleDateFormat;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.Calendar;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.Executors;
import java.util.stream.Collectors;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.boot.test.mock.mockito.SpyBean;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestTemplate;

// ruleid: mjg-boot-002-websecurityconfigureradapter
public class LegacySecurityConfig extends WebSecurityConfigurerAdapter {

    // ruleid: mjg-boot-004-autowired-field-injection
    @Autowired
    private Object userRepo;

    // ruleid: mjg-boot-008-mockbean-deprecated
    @MockBean
    private Object paymentGateway;

    // ruleid: mjg-boot-008-mockbean-deprecated
    @SpyBean
    private Object auditService;

    // ok: mjg-boot-008-mockbean-deprecated
    @MockitoBean
    private Object modernGateway;

    // ok: mjg-boot-004-autowired-field-injection
    private final RestClient restClient;

    // ruleid: mjg-boot-003-resttemplate
    private RestTemplate restTemplate;

    // ok: mjg-boot-004-autowired-field-injection
    @Autowired
    public LegacySecurityConfig(RestClient.Builder builder) {
        this.restClient = builder.build();
    }

    // ruleid: mjg-boot-003-resttemplate
    public RestTemplate legacyClient(RestTemplateBuilder builder) {
        // ruleid: mjg-boot-003-resttemplate
        return new RestTemplate();
    }

    public void legacyJavaPatterns(List<String> items, String user) {
        // ruleid: mjg-java-001-legacy-date-api
        Date now = new Date();
        // ruleid: mjg-java-001-legacy-date-api
        Calendar cal = Calendar.getInstance();
        // ruleid: mjg-java-001-legacy-date-api
        SimpleDateFormat fmt = new SimpleDateFormat("yyyy-MM-dd");
        // ok: mjg-java-001-legacy-date-api
        Instant modernNow = Instant.now();
        // ok: mjg-java-001-legacy-date-api
        DateTimeFormatter modernFmt = DateTimeFormatter.ISO_LOCAL_DATE;

        // ruleid: mjg-java-002-unmodifiable-aslist
        List<String> legacyList = Collections.unmodifiableList(Arrays.asList("a", "b"));
        // ok: mjg-java-002-unmodifiable-aslist
        List<String> modernList = List.of("a", "b");

        // ruleid: mjg-java-003-string-format
        String greeting = String.format("Hello, %s!", user);
        // ok: mjg-java-003-string-format
        String localized = String.format(Locale.US, "Hello, %s!", user);
        // ok: mjg-java-003-string-format
        String modernGreeting = "Hello, %s!".formatted(user);

        // ruleid: mjg-java-004-collectors-tolist
        List<String> collected = items.stream().collect(Collectors.toList());
        // ok: mjg-java-004-collectors-tolist
        List<String> modernCollected = items.stream().toList();

        // ruleid: mjg-java-010-platform-thread-pool
        var pool = Executors.newFixedThreadPool(8);
        // ruleid: mjg-java-010-platform-thread-pool
        var cached = Executors.newCachedThreadPool();
        // ok: mjg-java-010-platform-thread-pool
        var vpool = Executors.newVirtualThreadPerTaskExecutor();

        // ruleid: mjg-java-011-sequenced-get-last
        String last = items.get(items.size() - 1);
        // ok: mjg-java-011-sequenced-get-last
        String modernLast = items.getLast();
    }

    protected void configure(HttpSecurity http) throws Exception {
        // ruleid: mjg-boot-006-csrf-chained-disable
        http.csrf().disable();
        // ruleid: mjg-boot-006-csrf-chained-disable
        http
            .csrf()
            .disable();
        // ruleid: mjg-boot-005-security-legacy-matchers
        http.authorizeRequests();
        // ruleid: mjg-boot-005-security-legacy-matchers
        http.antMatchers("/public/**");
        // ruleid: mjg-boot-005-security-legacy-matchers
        http.mvcMatchers("/api/**");
    }

    // ok: mjg-boot-002-websecurityconfigureradapter
    @Bean
    SecurityFilterChain modernChain(HttpSecurity http) throws Exception {
        // ok: mjg-boot-005-security-legacy-matchers
        // ok: mjg-boot-006-csrf-chained-disable
        return http
            .csrf(AbstractHttpConfigurer::disable)
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/public/**").permitAll()
                .anyRequest().authenticated()
            )
            .build();
    }
}
