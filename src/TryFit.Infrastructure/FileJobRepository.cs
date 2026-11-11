using System.Collections.Concurrent;
using System.Text.Json;
using System.Text.Json.Serialization;
using TryFit.Application;
using TryFit.Domain;

namespace TryFit.Infrastructure;

public sealed class FileJobRepository : IJobRepository
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = true,
        Converters = { new JsonStringEnumConverter<JobStatus>(JsonNamingPolicy.CamelCase, allowIntegerValues: false) }
    };

    private readonly LocalWorkspace workspace;
    private readonly ConcurrentDictionary<Guid, TryFitJob> jobs = new();

    public FileJobRepository(LocalWorkspace workspace)
    {
        this.workspace = workspace;
        Directory.CreateDirectory(workspace.JobsDirectory);
        foreach (var directory in Directory.EnumerateDirectories(workspace.JobsDirectory))
        {
            if (!Guid.TryParseExact(Path.GetFileName(directory), "N", out var id))
                continue;

            var path = Path.Combine(directory, "job.json");
            if (!File.Exists(path))
                continue;

            try
            {
                var stored = JsonSerializer.Deserialize<StoredJob>(File.ReadAllText(path), Json);
                if (stored is not null && stored.Id == id)
                    jobs[id] = stored.ToDomain();
            }
            catch (JsonException)
            {
                // A damaged record cannot be recovered as a job.
            }
        }
    }

    public TryFitJob? Find(Guid id) => jobs.GetValueOrDefault(id);

    public IReadOnlyList<TryFitJob> ListActive() => jobs.Values.Where(job => job.IsActive).ToArray();

    public void Save(TryFitJob job)
    {
        var directory = workspace.JobDirectory(job.Id);
        Directory.CreateDirectory(directory);

        var path = Path.Combine(directory, "job.json");
        var temporaryPath = path + ".tmp";
        File.WriteAllText(temporaryPath, JsonSerializer.Serialize(StoredJob.FromDomain(job), Json));
        File.Move(temporaryPath, path, overwrite: true);
        jobs[job.Id] = job;
    }

    public Stream? OpenResult(Guid id)
    {
        var path = Path.Combine(workspace.JobDirectory(id), "result.png");
        return File.Exists(path) ? File.OpenRead(path) : null;
    }

    // Preserve the flat JSON written by the previous local app.
    private sealed record StoredJob(
        Guid Id, string ProfileId, string TopId, string BottomId, JobStatus Status, string Stage,
        DateTimeOffset CreatedAt, DateTimeOffset? StartedAt, DateTimeOffset? CompletedAt, string? Error,
        bool TuckTop = false)
    {
        public TryFitJob ToDomain() =>
            new(Id, new(ProfileId, TopId, BottomId, TuckTop), Status, Stage, CreatedAt, StartedAt, CompletedAt, Error);

        public static StoredJob FromDomain(TryFitJob job) =>
            new(job.Id, job.Selection.ProfileId, job.Selection.TopId, job.Selection.BottomId,
                job.Status, job.Stage, job.CreatedAt, job.StartedAt, job.CompletedAt, job.Error, job.Selection.TuckTop);
    }
}
