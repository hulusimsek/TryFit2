using TryFit.Application;
using TryFit.Domain;

namespace TryFit.Local;

internal static class TryOnEndpoints
{
    public static void MapTryOnEndpoints(this WebApplication app)
    {
        var api = app.MapGroup("/api");
        api.MapGet("/catalog", GetCatalog);
        api.MapGet("/health", (ITryOnEngine engine) => Results.Ok(new { ready = engine.IsReady, localOnly = true }));
        api.MapGet("/images/{kind}/{id}", GetCatalogImage);
        api.MapPost("/jobs", SubmitJob);
        api.MapGet("/jobs/{id:guid}", GetJob);
        api.MapGet("/jobs/{id:guid}/result", GetResult);
    }

    private static IResult GetCatalog(ICatalog catalog) => Results.Ok(new
    {
        profiles = catalog.Profiles.Values.Select(profile => new
        {
            profile.Id,
            profile.Label,
            ImageUrl = $"/api/images/profile/{profile.Id}"
        }),
        products = catalog.Products.Values.Select(product => new
        {
            product.Id,
            product.Label,
            Category = product.Category.ToString().ToLowerInvariant(),
            ImageUrl = $"/api/images/product/{product.Id}",
            product.ProductUrl
        }),
        scope = "Yerel araştırma denemesi. Seçilmiş ürünler ve hazır görsel profiller; ölçülü beden simülasyonu değildir."
    });

    private static IResult GetCatalogImage(string kind, string id, ICatalog catalog) =>
        catalog.OpenImage(kind, id) is { } image
            ? Results.Stream(image.Content, image.ContentType)
            : Results.NotFound();

    private static IResult SubmitJob(CreateJobRequest request, TryOnJobs jobs)
    {
        var selection = new OutfitSelection(
            request.ProfileId ?? string.Empty, request.TopId ?? string.Empty, request.BottomId ?? string.Empty, request.TuckTop);
        return jobs.Submit(selection) switch
        {
            { Status: SubmissionStatus.Accepted, Job: { } job } =>
                Results.Accepted($"/api/jobs/{job.Id}", JobResponse.From(job)),
            { Status: SubmissionStatus.InvalidSelection } =>
                Results.BadRequest(new { error = "Listeden bir profil, bir üst ve bir alt parça seç." }),
            { Status: SubmissionStatus.QueueFull } =>
                Results.Json(new { error = "İşlem sırası dolu. Mevcut deneme bittikten sonra tekrar dene." },
                    statusCode: StatusCodes.Status429TooManyRequests),
            _ => throw new InvalidOperationException("Unexpected job submission result.")
        };
    }

    private static IResult GetJob(Guid id, TryOnJobs jobs) =>
        jobs.Find(id) is { } job ? Results.Ok(JobResponse.From(job)) : Results.NotFound();

    private static IResult GetResult(Guid id, TryOnJobs jobs) =>
        jobs.OpenResult(id) is { } result ? Results.Stream(result, "image/png") : Results.NotFound();

    private sealed record CreateJobRequest(string? ProfileId, string? TopId, string? BottomId, bool TuckTop = false);

    private sealed record JobResponse(
        Guid Id, string ProfileId, string TopId, string BottomId, string Status, string Stage,
        DateTimeOffset CreatedAt, DateTimeOffset? StartedAt, DateTimeOffset? CompletedAt,
        string? Error, string? ResultUrl, bool TuckTop)
    {
        public static JobResponse From(TryFitJob job) =>
            new(job.Id, job.Selection.ProfileId, job.Selection.TopId, job.Selection.BottomId,
                job.Status.ToString().ToLowerInvariant(), job.Stage, job.CreatedAt, job.StartedAt, job.CompletedAt,
                job.Error, job.Status == JobStatus.Completed ? $"/api/jobs/{job.Id}/result" : null, job.Selection.TuckTop);
    }
}
