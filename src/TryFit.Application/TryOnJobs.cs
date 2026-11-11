using TryFit.Domain;

namespace TryFit.Application;

public enum SubmissionStatus { Accepted, InvalidSelection, QueueFull }

public sealed record Submission(SubmissionStatus Status, TryFitJob? Job = null);

public sealed class TryOnJobs(ICatalog catalog, IJobRepository repository, IJobQueue queue)
{
    private const int MaximumActiveJobs = 3;
    private readonly object submissionLock = new();

    public Submission Submit(OutfitSelection selection)
    {
        if (string.IsNullOrWhiteSpace(selection.ProfileId) || !catalog.Profiles.ContainsKey(selection.ProfileId)
            || !HasCategory(selection.TopId, GarmentCategory.Tops)
            || !HasCategory(selection.BottomId, GarmentCategory.Bottoms)
            || (selection.TuckTop && selection.BottomId != "skirt"))
        {
            return new(SubmissionStatus.InvalidSelection);
        }

        lock (submissionLock)
        {
            if (repository.ListActive().Count >= MaximumActiveJobs)
                return new(SubmissionStatus.QueueFull);

            var job = TryFitJob.Create(selection, DateTimeOffset.UtcNow);
            repository.Save(job);
            queue.Enqueue(job.Id);
            return new(SubmissionStatus.Accepted, job);
        }
    }

    public TryFitJob? Find(Guid id) => repository.Find(id);

    public Stream? OpenResult(Guid id) =>
        repository.Find(id)?.Status == JobStatus.Completed ? repository.OpenResult(id) : null;

    public void RecoverInterruptedJobs()
    {
        foreach (var job in repository.ListActive())
        {
            repository.Save(job.Fail("İşlem kesildi",
                "Uygulama yeniden açıldı. Kombini tekrar başlatabilirsin.", DateTimeOffset.UtcNow));
        }
    }

    private bool HasCategory(string id, GarmentCategory category) =>
        !string.IsNullOrWhiteSpace(id)
        && catalog.Products.TryGetValue(id, out var product)
        && product.Category == category;
}
