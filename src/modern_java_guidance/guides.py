"""On-demand searchable pattern catalog inspired by GoogleChrome/modern-web-guidance."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class GuideEntry:
    guide_id: str
    title: str
    min_java: int
    min_boot: str | None
    tags: tuple[str, ...]
    summary: str
    before_code: str
    after_code: str
    caveat: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.guide_id,
            "title": self.title,
            "min_java": self.min_java,
            "min_boot": self.min_boot,
            "tags": list(self.tags),
            "summary": self.summary,
            "before": self.before_code,
            "after": self.after_code,
            "caveat": self.caveat,
        }


GUIDES: tuple[GuideEntry, ...] = (
    GuideEntry(
        guide_id="JAVA-001",
        title="Replace java.util.Date & SimpleDateFormat with java.time",
        min_java=8,
        min_boot=None,
        tags=("date", "time", "instant", "simpledateformat", "thread-safe"),
        summary="Use immutable, thread-safe java.time types instead of Date/Calendar/SimpleDateFormat.",
        before_code="Date now = new Date();\nString s = new SimpleDateFormat(\"yyyy-MM-dd\").format(now);",
        after_code="Instant now = Instant.now();\nString s = DateTimeFormatter.ISO_LOCAL_DATE.format(LocalDate.now());",
        caveat="Keep java.util.Date only at legacy JDBC/SOAP boundaries via Date.from(instant) / instant.toInstant().",
    ),
    GuideEntry(
        guide_id="JAVA-002",
        title="Use Immutable Collection Factories (List.of / Set.of / Map.of)",
        min_java=9,
        min_boot=None,
        tags=("collections", "list", "set", "map", "immutable"),
        summary="Replace Collections.unmodifiableList(Arrays.asList(...)) with List.of/Set.of/Map.of.",
        before_code='List<String> roles = Collections.unmodifiableList(Arrays.asList("USER", "ADMIN"));',
        after_code='List<String> roles = List.of("USER", "ADMIN");',
        caveat="List.of/Set.of/Map.of reject null elements; use Collections.unmodifiableList if nulls are required.",
    ),
    GuideEntry(
        guide_id="JAVA-003",
        title="Use String.formatted() Instead of String.format()",
        min_java=15,
        min_boot=None,
        tags=("string", "format", "readability"),
        summary="Call .formatted(...) directly on string literals or text blocks.",
        before_code='String msg = String.format("User %s (%d)", name, id);',
        after_code='String msg = "User %s (%d)".formatted(name, id);',
        caveat="Keep String.format(Locale, ...) when an explicit Locale is required.",
    ),
    GuideEntry(
        guide_id="JAVA-010",
        title="Use Virtual Threads for Blocking I/O Workloads",
        min_java=21,
        min_boot=None,
        tags=("virtual-threads", "executor", "concurrency", "thread-pool"),
        summary="Prefer Executors.newVirtualThreadPerTaskExecutor() over fixed/cached pools for blocking I/O.",
        before_code="ExecutorService pool = Executors.newFixedThreadPool(16);",
        after_code="try (var pool = Executors.newVirtualThreadPerTaskExecutor()) {\n    pool.submit(() -> callRemoteService());\n}",
        caveat="Keep bounded pools or Semaphores for CPU-bound work or downstream rate limiting.",
    ),
    GuideEntry(
        guide_id="JAVA-011",
        title="Use SequencedCollection.getFirst() / getLast() / reversed()",
        min_java=21,
        min_boot=None,
        tags=("sequenced", "list", "getlast", "getfirst", "collections"),
        summary="Replace list.get(list.size() - 1) and list.get(0) with SequencedCollection methods.",
        before_code="String first = items.get(0);\nString last = items.get(items.size() - 1);",
        after_code="String first = items.getFirst();\nString last = items.getLast();",
        caveat="Check !items.isEmpty() first; getFirst()/getLast() throw NoSuchElementException on empty collections.",
    ),
    GuideEntry(
        guide_id="JAVA-012",
        title="Use Records, Sealed Interfaces & Pattern Matching for switch",
        min_java=21,
        min_boot=None,
        tags=("record", "sealed", "switch", "pattern-matching", "dto"),
        summary="Model closed algebraic data types with sealed interfaces + records and exhaustive switch.",
        before_code="if (res instanceof Approved) {\n    Approved a = (Approved) res;\n    return a.getTxId();\n}",
        after_code="return switch (res) {\n    case Approved(var txId, var amt) -> txId;\n    case Declined(var reason) -> throw new IllegalStateException(reason);\n};",
        caveat="Do not use Java records for JPA @Entity classes (entities require mutable state and no-arg constructors).",
    ),
    GuideEntry(
        guide_id="BOOT-001",
        title="Migrate javax.* EE Imports to jakarta.* (Jakarta EE 10)",
        min_java=17,
        min_boot="3.0",
        tags=("jakarta", "javax", "jpa", "validation", "servlet", "boot3"),
        summary="Spring Boot 3+ uses Jakarta EE 10 (jakarta.*); javax.* persistence/validation/servlet fail to compile.",
        before_code="import javax.persistence.Entity;\nimport javax.validation.constraints.NotBlank;",
        after_code="import jakarta.persistence.Entity;\nimport jakarta.validation.constraints.NotBlank;",
        caveat="Standard JDK packages like javax.sql.* and javax.crypto.* stay javax.*.",
    ),
    GuideEntry(
        guide_id="BOOT-002",
        title="Replace WebSecurityConfigurerAdapter with SecurityFilterChain Bean",
        min_java=17,
        min_boot="3.0",
        tags=("security", "securityfilterchain", "websecurityconfigureradapter", "boot3"),
        summary="WebSecurityConfigurerAdapter was removed in Spring Security 6; expose a @Bean SecurityFilterChain.",
        before_code="public class SecurityConfig extends WebSecurityConfigurerAdapter {\n    @Override\n    protected void configure(HttpSecurity http) throws Exception { ... }\n}",
        after_code="@Configuration\npublic class SecurityConfig {\n    @Bean\n    SecurityFilterChain filterChain(HttpSecurity http) throws Exception {\n        return http.authorizeHttpRequests(a -> a.anyRequest().authenticated()).build();\n    }\n}",
        caveat="Avoid @EnableWebSecurity(debug = true) in production.",
    ),
    GuideEntry(
        guide_id="BOOT-003",
        title="Use RestClient or @HttpExchange Instead of RestTemplate",
        min_java=17,
        min_boot="3.2",
        tags=("http", "restclient", "resttemplate", "httpexchange", "client"),
        summary="Spring Boot 3.2+ provides the fluent synchronous RestClient and declarative @HttpExchange interfaces.",
        before_code="RestTemplate rt = new RestTemplate();\nString body = rt.getForObject(url, String.class);",
        after_code="RestClient client = builder.baseUrl(baseUrl).build();\nString body = client.get().uri(path).retrieve().body(String.class);",
        caveat="Use WebClient when building reactive WebFlux applications.",
    ),
    GuideEntry(
        guide_id="BOOT-004",
        title="Prefer Constructor Injection Over @Autowired Field Injection",
        min_java=17,
        min_boot="3.0",
        tags=("di", "autowired", "constructor", "spring", "testing"),
        summary="Use private final fields with constructor injection (omit @Autowired on single constructors).",
        before_code="@Autowired\nprivate OrderRepository orderRepository;",
        after_code="private final OrderRepository orderRepository;\n\npublic OrderService(OrderRepository orderRepository) {\n    this.orderRepository = orderRepository;\n}",
        caveat="Makes dependencies immutable and enables plain unit tests without a Spring context.",
    ),
    GuideEntry(
        guide_id="BOOT-005",
        title="Use authorizeHttpRequests() & requestMatchers() in Security 6",
        min_java=17,
        min_boot="3.0",
        tags=("security", "antmatchers", "requestmatchers", "authorizerequests"),
        summary="Replace removed authorizeRequests()/antMatchers()/mvcMatchers() with authorizeHttpRequests/requestMatchers.",
        before_code='http.authorizeRequests().antMatchers("/public/**").permitAll();',
        after_code='http.authorizeHttpRequests(auth -> auth.requestMatchers("/public/**").permitAll().anyRequest().authenticated());',
        caveat="Order matters: declare specific public matchers before anyRequest().authenticated().",
    ),
    GuideEntry(
        guide_id="BOOT-006",
        title="Use Spring Security 6 Lambda DSL for CSRF & Session Config",
        min_java=17,
        min_boot="3.0",
        tags=("security", "csrf", "lambda-dsl", "boot3"),
        summary="Replace deprecated chained .csrf().disable() with Lambda DSL; keep CSRF enabled by default.",
        before_code="http.csrf().disable();",
        after_code="http.csrf(AbstractHttpConfigurer::disable); // only for Bearer/token auth, never HTTP Basic or cookies",
        caveat="Keep CSRF enabled by default; stateless sessions do not protect HTTP Basic or cookie auth in browsers. Only disable CSRF for non-browser-attached credentials (e.g. Bearer JWT).",
    ),
    GuideEntry(
        guide_id="BOOT-007",
        title="Return RFC 9457 ProblemDetail from @RestControllerAdvice",
        min_java=17,
        min_boot="3.0",
        tags=("error", "problemdetail", "exception", "restcontrolleradvice", "rfc9457"),
        summary="Use Spring 6 / Boot 3 built-in ProblemDetail for standardized HTTP error responses.",
        before_code="return ResponseEntity.badRequest().body(Map.of(\"error\", ex.getMessage()));",
        after_code="ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, ex.getMessage());\npd.setTitle(\"Invalid Request\");\nreturn pd;",
        caveat="Enable spring.mvc.problemdetails.enabled=true for automatic framework exception mapping.",
    ),
)


def search_guides(query: str) -> list[GuideEntry]:
    """Search guides by ID, title, summary, or tags (case-insensitive)."""
    terms = [t.strip().lower() for t in query.split() if t.strip()]
    if not terms:
        return list(GUIDES)

    matches: list[GuideEntry] = []
    for entry in GUIDES:
        haystack = " ".join(
            [
                entry.guide_id,
                entry.title,
                entry.summary,
                *entry.tags,
            ]
        ).lower()
        if all(term in haystack for term in terms):
            matches.append(entry)
    return matches


def retrieve_guide(guide_id: str) -> GuideEntry | None:
    """Retrieve a single guide by exact ID (case-insensitive)."""
    target = guide_id.strip().upper()
    for entry in GUIDES:
        if entry.guide_id == target:
            return entry
    return None
