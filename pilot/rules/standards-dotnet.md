---
paths:
  - "**/*.cs"
  - "**/*.csproj"
  - "**/*.sln"
---

## .NET Development Standards

**Standards:** Always use dotnet CLI  | dotnet format for quality | Self-documenting code

### CLI Usage

**MANDATORY: Use `dotnet` CLI for all operations.**

```bash
dotnet build
dotnet run --project src/MyApp
dotnet test
dotnet add package PackageName
```

### Testing & Quality

**Use minimal output flags to avoid context bloat.**

```bash
dotnet test -v q                                     # Quiet mode (preferred)
# AVOID -v d, -v diag unless actively debugging

dotnet format                                        # Format
dotnet format --verify-no-changes                    # Check formatting (CI)
```

### Code Style

- **XML docs:** One-line `<summary>` for most members. Multi-line only for complex logic. Skip when name is self-explanatory.
- **Naming:** PascalCase for public members, `camelCase` for private fields, camelCase for locals/parameters.
- **Usings:** `global using` for common namespaces. File-scoped namespaces preferred (`namespace MyApp;`).
- **Comments:** Only for complex algorithms, non-obvious logic, or workarounds.

### Common Patterns

- **No bare `catch`:** Catch specific exceptions, log, and re-throw with `throw;` (not `throw ex;`)
- **IDisposable:** `using var stream = new FileStream(...)` for resources
- **Async all the way:** `async Task` over `async void`. Suffix async methods with `Async`. **Never block on async code** — no `.Result`, `.Wait()`, or `GetAwaiter().GetResult()` in application code. Use `await` instead.
- **Null-safe patterns:** Enable `<Nullable>enable</Nullable>`. Use `string?` for nullable, never `null!` without justification. Prefer null-conditional (`?.`), null-coalescing (`??`, `??=`), and `is not null` checks. Avoid `== null` comparisons.
- **Records for DTOs:** `public record OrderDto(string Name, decimal Price);`
- **Pattern matching:** Prefer `is`, `switch` expressions over chains of `if`/`else`

### Project Configuration

- .NET 8+ (`<TargetFramework>net8.0</TargetFramework>` or newer)
- Dependencies in `.csproj`
- Enable `<ImplicitUsings>enable</ImplicitUsings>`
- Enable `<Nullable>enable</Nullable>`
- Enable `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>` — all warnings are build failures
- Enable built-in analyzers: `<EnableNETAnalyzers>true</EnableNETAnalyzers>` with `<AnalysisLevel>latest-recommended</AnalysisLevel>`
- Use `[Trait("Category", "Unit")]` and `[Trait("Category", "Integration")]` for test categorization

### ASP.NET Best Practices

- **Minimal APIs** for simple endpoints; controllers for complex domains with shared filters/conventions.
- **Dependency injection:** Register services in `Program.cs`. Use `AddScoped` for request-scoped, `AddSingleton` for stateless services. Never resolve via `IServiceProvider` manually unless in a factory.
- **Configuration:** Bind to strongly-typed options via `IOptions<T>` / `IOptionsSnapshot<T>`. Never read `IConfiguration` directly in services.
- **Middleware order matters:** Authentication → Authorization → CORS → Routing → Endpoints. Place custom middleware deliberately.
- **Validation:** Use `FluentValidation` or Data Annotations. Validate at the API boundary, not deep in domain logic.
- **Error handling:** Use `ProblemDetails` for consistent error responses. Configure `app.UseExceptionHandler()` — never leak stack traces in production.
- **Logging:** Inject `ILogger<T>`. Use structured logging with message templates (`Log.Information("Order {OrderId} placed", id)`). Never string-interpolate log messages.
- **HTTP clients:** Use `IHttpClientFactory` / typed clients. Never `new HttpClient()` directly — causes socket exhaustion.
- **Authentication/Authorization:** Use policy-based authorization (`[Authorize(Policy = "Admin")]`). Keep auth logic out of controllers.
- **Response caching & compression:** Enable `ResponseCompression` middleware. Use `[ResponseCache]` or output caching where appropriate.
- **Health checks:** Register `app.MapHealthChecks("/health")` for readiness/liveness probes.
- **CORS:** Configure explicitly with named policies. Never use `AllowAnyOrigin` + `AllowCredentials` together.

### Verification Checklist

- [ ] `dotnet build` — compiles clean (zero warnings, TreatWarningsAsErrors enforced)
- [ ] `dotnet test` — tests pass
- [ ] No analyzer violations
- [ ] `dotnet format --verify-no-changes` — formatted
- [ ] No nullable warnings
- [ ] Coverage ≥ 80%
- [ ] No unused usings
- [ ] Production files ideally under 800 lines (1000+ = consider splitting)
