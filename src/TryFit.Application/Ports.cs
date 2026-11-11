using TryFit.Domain;

namespace TryFit.Application;

public enum GarmentCategory { Tops, Bottoms }
public enum TryOnStage { Upper, Lower }

public sealed record Profile(string Id, string Label);
public sealed record Product(string Id, string Label, GarmentCategory Category, string ProductUrl);
public sealed record CatalogImage(Stream Content, string ContentType);

public interface ICatalog
{
    IReadOnlyDictionary<string, Profile> Profiles { get; }
    IReadOnlyDictionary<string, Product> Products { get; }
    CatalogImage? OpenImage(string kind, string id);
}

public interface IJobRepository
{
    TryFitJob? Find(Guid id);
    IReadOnlyList<TryFitJob> ListActive();
    void Save(TryFitJob job);
    Stream? OpenResult(Guid id);
}

public interface IJobQueue
{
    void Enqueue(Guid id);
    IAsyncEnumerable<Guid> ReadAllAsync(CancellationToken cancellationToken);
}

public interface ITryOnEngine
{
    bool IsReady { get; }
    Task GenerateAsync(TryFitJob job, Action<TryOnStage> reportStage, CancellationToken cancellationToken);
}
