using System.Text.Json;
using TryFit.Application;

namespace TryFit.Infrastructure;

public sealed class ManifestCatalog : ICatalog
{
    private static readonly HashSet<string> SelectedProducts =
        ["tshirt", "patterned-blouse", "wide-trousers", "skirt"];

    private readonly Dictionary<(string Kind, string Id), string> images = new();

    public ManifestCatalog(LocalWorkspace workspace)
    {
        var profiles = new Dictionary<string, Profile>(StringComparer.Ordinal);
        foreach (var entry in ReadEntries(workspace, "avatar-profiles.json", "profiles"))
        {
            var id = ReadString(entry, "id");
            profiles.Add(id, new(id, ReadString(entry, "label")));
            images.Add(("profile", id), ResolveImage(workspace, entry));
        }

        var products = new Dictionary<string, Product>(StringComparer.Ordinal);
        foreach (var entry in ReadEntries(workspace, "trendyol-10.actual.json", "cases"))
        {
            var id = ReadString(entry, "id");
            if (!SelectedProducts.Contains(id))
                continue;

            var category = ReadString(entry, "category") switch
            {
                "tops" => GarmentCategory.Tops,
                "bottoms" => GarmentCategory.Bottoms,
                _ => throw new InvalidDataException($"Unsupported category for {id}.")
            };
            products.Add(id, new(id, ReadString(entry, "label"), category, ReadString(entry, "product_url")));
            images.Add(("product", id), ResolveImage(workspace, entry));
        }

        if (profiles.Count != 3 || products.Count != SelectedProducts.Count)
            throw new InvalidDataException("Örnek katalog eksik.");

        Profiles = profiles;
        Products = products;
    }

    public IReadOnlyDictionary<string, Profile> Profiles { get; }
    public IReadOnlyDictionary<string, Product> Products { get; }

    public CatalogImage? OpenImage(string kind, string id)
    {
        if (!images.TryGetValue((kind, id), out var path) || !File.Exists(path))
            return null;

        var contentType = Path.GetExtension(path).Equals(".png", StringComparison.OrdinalIgnoreCase)
            ? "image/png"
            : "image/jpeg";
        return new(File.OpenRead(path), contentType);
    }

    private static IEnumerable<JsonElement> ReadEntries(LocalWorkspace workspace, string manifest, string property)
    {
        using var document = JsonDocument.Parse(
            File.ReadAllText(Path.Combine(workspace.Root, "evaluation", "manifests", manifest)));
        foreach (var entry in document.RootElement.GetProperty(property).EnumerateArray())
            yield return entry;
    }

    private static string ResolveImage(LocalWorkspace workspace, JsonElement entry)
    {
        var path = Path.GetFullPath(ReadString(entry, "image"), workspace.Root);
        var relativePath = Path.GetRelativePath(workspace.Root, path);
        if (Path.IsPathRooted(relativePath) || relativePath == ".."
            || relativePath.StartsWith(".." + Path.DirectorySeparatorChar, StringComparison.Ordinal)
            || !File.Exists(path))
        {
            throw new InvalidDataException("Katalog görseli geçersiz.");
        }

        return path;
    }

    private static string ReadString(JsonElement entry, string property) =>
        entry.GetProperty(property).GetString() ?? throw new InvalidDataException($"Missing catalog field: {property}.");
}
