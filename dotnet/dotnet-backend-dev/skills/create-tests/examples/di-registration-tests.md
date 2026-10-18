# DI Registration Tests - BaseDependencyInjectionTests

Use `BaseDependencyInjectionTests` for verifying that services are correctly registered in the DI container.

The code examples in this file use NUnit and FluentAssertions. With another test framework or assertion library, use its equivalent attributes and calls.

## Base Class

Location: `<Project>.Tests.Common.ForTests.BaseDependencyInjectionTests` (one for each service: use the Tests.Common namespace of your repository)

Inherits from: `BaseMockTest` (provides the `Fixture` of the test data library for mocking)

## Available Helper Methods

```csharp
// Create empty ServiceCollection for testing
protected static ServiceCollection CreateServiceCollection();

// Create HostApplicationBuilder for testing (includes Configuration)
protected static HostApplicationBuilder CreateHostAppBuilder();

// Assert service is NOT registered
protected void AssertOn_NotRegistered<T>(ServiceProvider serviceProvider);

// Assert service is registered (returns all instances)
protected IEnumerable<T> AssertOn_RegisteredService<T>(ServiceProvider serviceProvider);

// Assert registered service is specific implementation type
protected void AssertOn_RegisteredServiceBeOfType<TService, TExpected>(ServiceProvider serviceProvider);

// Assert registered service is NOT specific type
protected void AssertOn_RegisteredServiceNotBeOfType<TService, TNotExpected>(ServiceProvider serviceProvider);

// Assert transient lifetime (different instances each resolve)
protected T AssertOn_TransientService<T>(ServiceProvider serviceProvider);
protected void AssertOn_TransientServiceBeOfType<TService, TExpected>(ServiceProvider serviceProvider);
protected void AssertOn_TransientServiceNotBeOfType<TService, TNotExpected>(ServiceProvider serviceProvider);

// Assert singleton lifetime (same instance each resolve)
protected T AssertOn_SingletonService<T>(ServiceProvider serviceProvider);
protected void AssertOn_SingletonServiceBeOfType<TService, TExpected>(ServiceProvider serviceProvider);
protected void AssertOn_SingletonServiceNotBeOfType<TService, TNotExpected>(ServiceProvider serviceProvider);
```

## Complete Example

```csharp
// Copyright (c) Vasily Vasilyev

using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using MyApp.Framework.Configuration.Options.Logging.WebApi;
using MyApp.Framework.Configuration.Options.WebApi.Versioning;
using MyApp.Framework.Infrastructure.Hosting.Builders.Hosts;
using MyApp.Framework.Infrastructure.WebApi.Configuration;
using MyApp.Framework.Infrastructure.WebApi.Diagnostics;
using MyApp.Framework.Infrastructure.WebApi.Diagnostics.Problems;

namespace MyApp.Framework.Tests.Infrastructure.WebApi.Configuration;

[TestFixture]
[Parallelizable(ParallelScope.Fixtures)]
public sealed class WebApiDependencyInjectionTests : BaseDependencyInjectionTests
{
    public WebApiDependencyInjectionTests()
    {
    }

    [Test]
    public void AddSharedWebApiServices_OnNullServiceCollection_ThrowsArgumentNullException()
    {
        // Arrange.
        ServiceCollection? serviceCollection = null;

        // Act.
        var act = () => serviceCollection!.AddSharedWebApiServices();

        // Assert.
        act.Should().Throw<ArgumentNullException>();
    }

    [Test]
    public void AddSharedWebApiServices_RegistersHttpContextAccessor_AsSingleton()
    {
        // Arrange.
        var serviceCollection = CreateServiceCollection();

        // Act.
        RegisterServices(serviceCollection);
        using var provider = serviceCollection.BuildServiceProvider();

        // Assert.
        AssertOn_SingletonService<IHttpContextAccessor>(provider);
    }

    [Test]
    public void AddSharedWebApiServices_RegistersProblemUriProvider_AsTransient()
    {
        // Arrange.
        var serviceCollection = CreateServiceCollection();

        // Act.
        RegisterServices(serviceCollection);
        using var provider = serviceCollection.BuildServiceProvider();

        // Assert.
        AssertOn_TransientService<IProblemUriProvider>(provider);
    }

    [Test]
    public void AddSharedWebApiServices_RegistersErrorFactory_AsTransient()
    {
        // Arrange.
        var serviceCollection = CreateServiceCollection();

        // Act.
        RegisterServices(serviceCollection);
        using var provider = serviceCollection.BuildServiceProvider();

        // Assert.
        AssertOn_TransientService<IErrorFactory>(provider);
    }

    [Test]
    public void ConfigureHttpLogging_OnNullServiceCollection_ThrowsArgumentNullException()
    {
        // Arrange.
        ServiceCollection? serviceCollection = null;

        // Act.
        var act = () => serviceCollection!.ConfigureHttpLogging();

        // Assert.
        act.Should().Throw<ArgumentNullException>();
    }

    [Test]
    public void ConfigureHttpLogging_WithEnabledLogging_InvokesConfigureAction()
    {
        // Arrange.
        var hostAppBuilder = CreateHostAppBuilder();
        hostAppBuilder.ConfigureOptionsAndEnableValidation<WebApiHttpLoggingOptions>(
            configureOptions: options => options.IsEnabled = true);

        var wasCalled = false;

        // Act.
        hostAppBuilder.Services.ConfigureHttpLogging(ConfigureAction);

        // Assert.
        wasCalled.Should().BeTrue();

        return;

        void ConfigureAction(IServiceCollection sc, WebApiHttpLoggingOptions options)
        {
            wasCalled = true;
        }
    }

    [Test]
    public void ConfigureHttpLogging_WithEnabledLogging_ButNoAction_ThrowsException()
    {
        // Arrange.
        var hostAppBuilder = CreateHostAppBuilder();
        hostAppBuilder.ConfigureOptionsAndEnableValidation<WebApiHttpLoggingOptions>(
            configureOptions: options => options.IsEnabled = true);

        // Act.
        var act = () => hostAppBuilder.Services.ConfigureHttpLogging();

        // Assert.
        act.Should().Throw<ArgumentException>();
    }

    [Test]
    public void ConfigureHttpLogging_WithDisabledLogging_DoesNotInvokeConfigureAction()
    {
        // Arrange.
        var hostAppBuilder = CreateHostAppBuilder();
        hostAppBuilder.ConfigureOptionsAndEnableValidation<WebApiHttpLoggingOptions>(
            configureOptions: options => options.IsEnabled = false);

        var wasCalled = false;

        // Act.
        hostAppBuilder.Services.ConfigureHttpLogging(ConfigureAction);

        // Assert.
        wasCalled.Should().BeFalse();

        return;

        void ConfigureAction(IServiceCollection sc, WebApiHttpLoggingOptions options)
        {
            wasCalled = true;
        }
    }

    [Test]
    public void AddAppApiVersioning_OnNullServiceCollection_ThrowsArgumentNullException()
    {
        // Arrange.
        ServiceCollection? serviceCollection = null;

        // Act.
        var act = () => serviceCollection!.AddAppApiVersioning();

        // Assert.
        act.Should().Throw<ArgumentNullException>();
    }

    [Test]
    public void AddAppApiVersioning_RegistersVersioningServices()
    {
        // Arrange.
        var hostAppBuilder = CreateHostAppBuilder();
        hostAppBuilder.ConfigureOptionsAndEnableValidation<AppVersioningRegistratorOptions>();

        var wasCalled = false;

        // Act.
        hostAppBuilder.Services.AddAppApiVersioning(ConfigureAction);

        // Assert.
        wasCalled.Should().BeTrue();

        return;

        void ConfigureAction(IServiceCollection sc, AppVersioningRegistratorOptions options)
        {
            wasCalled = true;
        }
    }

    [Test]
    public void AddAppDiagnosticServices_OnNullServiceCollection_ThrowsArgumentNullException()
    {
        // Arrange.
        ServiceCollection? serviceCollection = null;

        // Act.
        var act = () => serviceCollection!.AddAppDiagnosticServices();

        // Assert.
        act.Should().Throw<ArgumentNullException>();
    }

    [Test]
    public void AddAppDiagnosticServices_RegistersVersioningServices()
    {
        // Arrange.
        var serviceCollection = CreateServiceCollection();

        // Act.
        serviceCollection.AddAppDiagnosticServices(
            useCustomizedProblemDetailsHandler: true,
            ConfigureAction);
        using var provider = serviceCollection.BuildServiceProvider();

        // Assert.
        // AddAppDiagnosticServices does not call delegate action immediately,
        // it only registers it using Configure call.
        AssertOn_RegisteredService<IConfigureOptions<ProblemDetailsOptions>>(provider);

        return;

        static void ConfigureAction(ProblemDetailsOptions options)
        {
        }
    }

    [Test]
    public void AddAppAppSwaggerGen_OnNullServiceCollection_ThrowsArgumentNullException()
    {
        // Arrange.
        ServiceCollection? serviceCollection = null;

        // Act.
        var act = () => serviceCollection!.AddAppAppSwaggerGen();

        // Assert.
        act.Should().Throw<ArgumentNullException>();
    }

    private static void RegisterServices(ServiceCollection serviceCollection)
    {
        serviceCollection.AddLogging();
        serviceCollection.AddSharedWebApiServices();
    }
}
```

## Test Patterns

### 1. Null ServiceCollection Validation

```csharp
[Test]
public void AddMyServices_OnNullServiceCollection_ThrowsArgumentNullException()
{
    // Arrange.
    ServiceCollection? serviceCollection = null;

    // Act.
    var act = () => serviceCollection!.AddMyServices();

    // Assert.
    act.Should().Throw<ArgumentNullException>();
}
```

### 2. Service Lifetime Verification

```csharp
[Test]
public void AddMyServices_RegistersMyService_AsSingleton()
{
    // Arrange.
    var serviceCollection = CreateServiceCollection();

    // Act.
    RegisterServices(serviceCollection);
    using var provider = serviceCollection.BuildServiceProvider();

    // Assert.
    AssertOn_SingletonService<IMyService>(provider);
}

[Test]
public void AddMyServices_RegistersMyService_AsTransient()
{
    // Arrange.
    var serviceCollection = CreateServiceCollection();

    // Act.
    RegisterServices(serviceCollection);
    using var provider = serviceCollection.BuildServiceProvider();

    // Assert.
    AssertOn_TransientService<IMyService>(provider);
}
```

### 3. Configuration-Dependent Registration

```csharp
[Test]
public void ConfigureFeature_WithEnabledOption_InvokesConfigureAction()
{
    // Arrange.
    var hostAppBuilder = CreateHostAppBuilder();
    hostAppBuilder.ConfigureOptionsAndEnableValidation<FeatureOptions>(
        configureOptions: options => options.IsEnabled = true);

    var wasCalled = false;

    // Act.
    hostAppBuilder.Services.ConfigureFeature(ConfigureAction);

    // Assert.
    wasCalled.Should().BeTrue();

    return;

    void ConfigureAction(IServiceCollection sc, FeatureOptions options)
    {
        wasCalled = true;
    }
}

[Test]
public void ConfigureFeature_WithDisabledOption_DoesNotInvokeConfigureAction()
{
    // Arrange.
    var hostAppBuilder = CreateHostAppBuilder();
    hostAppBuilder.ConfigureOptionsAndEnableValidation<FeatureOptions>(
        configureOptions: options => options.IsEnabled = false);

    var wasCalled = false;

    // Act.
    hostAppBuilder.Services.ConfigureFeature(ConfigureAction);

    // Assert.
    wasCalled.Should().BeFalse();

    return;

    void ConfigureAction(IServiceCollection sc, FeatureOptions options)
    {
        wasCalled = true;
    }
}
```

### 4. Delayed Registration (Configure Pattern)

```csharp
[Test]
public void AddDiagnosticServices_RegistersConfigureOptions()
{
    // Arrange.
    var serviceCollection = CreateServiceCollection();

    // Act.
    serviceCollection.AddDiagnosticServices(ConfigureAction);
    using var provider = serviceCollection.BuildServiceProvider();

    // Assert.
    // The delegate is not called immediately - it's registered via Configure<T>
    AssertOn_RegisteredService<IConfigureOptions<DiagnosticOptions>>(provider);

    return;

    static void ConfigureAction(DiagnosticOptions options)
    {
    }
}
```

## Key Points

1. **Use `CreateServiceCollection()`** for simple registration tests

2. **Use `CreateHostAppBuilder()`** for tests of configuration-dependent registration

3. **Always dispose ServiceProvider**: use `using var provider`

4. **Test both positive and negative**: verify services ARE registered AND throw on null

5. **Test conditional logic**: verify feature toggles/options affect registration

6. **Private helper method**: extract common registration setup to `RegisterServices()`
