# Serialized Output Examples

Code for "Example: JSON Converter for a Secret Wrapper" in `SKILL.md`: the converter and a call that serializes the wrapper.

```csharp
using System.Text.Json;
using System.Text.Json.Serialization;
using MyApp.Framework.Constants;

namespace MyApp.Domain.Security;

/// <summary>
/// Writes the erased placeholder in place of the value of an <see cref="ApiSecretToken"/>.
/// </summary>
public sealed class ApiSecretTokenJsonConverter : JsonConverter<ApiSecretToken>
{
    private static String DefaultErasedPlaceholder => Constants.DefaultErasedPlaceholder;

    // ✅ CRITICAL - the JSON gets the placeholder, never the token
    public override void Write(
        Utf8JsonWriter writer,
        ApiSecretToken value,
        JsonSerializerOptions options)
    {
        writer.WriteStringValue(DefaultErasedPlaceholder);
    }

    // No round trip - the placeholder is not the token
    public override ApiSecretToken Read(
        ref Utf8JsonReader reader,
        Type typeToConvert,
        JsonSerializerOptions options)
    {
        throw new NotSupportedException(
            $"{nameof(ApiSecretToken)} cannot be read from JSON. Its JSON form holds only the placeholder.");
    }
}

// Register the converter on the wrapper type
[JsonConverter(typeof(ApiSecretTokenJsonConverter))]
public readonly record struct ApiSecretToken : IStringWrapper<ApiSecretToken>
{
    // Members as in "Example: Primitive Wrapper with Secret"
}
```

```csharp
var json = JsonSerializer.Serialize(new
{
    Endpoint = "https://api.example.com",
    Token = ApiSecretToken.FromValue("s3cr3t"),
});
// {"Endpoint":"https://api.example.com","Token":"<the placeholder>"}
```
