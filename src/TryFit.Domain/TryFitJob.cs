namespace TryFit.Domain;

public enum JobStatus
{
    Queued,
    Running,
    Completed,
    Failed
}

public sealed record OutfitSelection(string ProfileId, string TopId, string BottomId, bool TuckTop = false);

public sealed record TryFitJob(
    Guid Id,
    OutfitSelection Selection,
    JobStatus Status,
    string Stage,
    DateTimeOffset CreatedAt,
    DateTimeOffset? StartedAt = null,
    DateTimeOffset? CompletedAt = null,
    string? Error = null)
{
    public bool IsActive => Status is JobStatus.Queued or JobStatus.Running;

    public static TryFitJob Create(OutfitSelection selection, DateTimeOffset now) =>
        new(Guid.NewGuid(), selection, JobStatus.Queued, "Sıraya alındı", now);

    public TryFitJob Start(DateTimeOffset now)
    {
        EnsureStatus(JobStatus.Queued);
        return this with { Status = JobStatus.Running, Stage = "Model hazırlanıyor", StartedAt = now };
    }

    public TryFitJob ReportStage(string stage)
    {
        EnsureStatus(JobStatus.Running);
        return this with { Stage = stage };
    }

    public TryFitJob Complete(DateTimeOffset now)
    {
        EnsureStatus(JobStatus.Running);
        return this with { Status = JobStatus.Completed, Stage = "Kombin hazır", CompletedAt = now };
    }

    public TryFitJob Fail(string stage, string error, DateTimeOffset now)
    {
        if (!IsActive)
            throw new InvalidOperationException($"Cannot fail a {Status} job.");

        return this with { Status = JobStatus.Failed, Stage = stage, Error = error, CompletedAt = now };
    }

    private void EnsureStatus(JobStatus expected)
    {
        if (Status != expected)
            throw new InvalidOperationException($"Expected job status {expected}, found {Status}.");
    }
}
