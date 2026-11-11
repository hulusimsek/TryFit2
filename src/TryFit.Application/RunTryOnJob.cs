using TryFit.Domain;

namespace TryFit.Application;

public sealed class RunTryOnJob(IJobRepository repository, ITryOnEngine engine)
{
    public async Task ExecuteAsync(Guid id, CancellationToken cancellationToken)
    {
        var job = repository.Find(id);
        if (job is null || job.Status != JobStatus.Queued)
            return;

        job = job.Start(DateTimeOffset.UtcNow);
        try
        {
            repository.Save(job);
            await engine.GenerateAsync(job, stage =>
            {
                var description = stage == TryOnStage.Upper ? "Üst parça deneniyor" : "Alt parça deneniyor";
                job = job.ReportStage(description);
                repository.Save(job);
            }, cancellationToken);
            repository.Save(job.Complete(DateTimeOffset.UtcNow));
        }
        catch (Exception)
        {
            repository.Save(job.Fail("İşlem tamamlanamadı",
                "Üretim tamamlanamadı. Kaynak görüntülerini ve yerel model ortamını kontrol edip tekrar dene.",
                DateTimeOffset.UtcNow));
            throw;
        }
    }
}
