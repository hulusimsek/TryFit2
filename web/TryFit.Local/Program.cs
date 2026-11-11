using TryFit.Application;
using TryFit.Infrastructure;
using TryFit.Local;

var configuredWorkspace = Environment.GetEnvironmentVariable("TRYFIT_WORKSPACE");
var options = new WebApplicationOptions
{
    Args = args,
    ContentRootPath = string.IsNullOrWhiteSpace(configuredWorkspace)
        ? null
        : Path.Combine(Path.GetFullPath(configuredWorkspace), "web", "TryFit.Local")
};

var builder = WebApplication.CreateBuilder(options);
var workspace = new LocalWorkspace(configuredWorkspace ?? Path.Combine(builder.Environment.ContentRootPath, "../.."));
builder.WebHost.UseUrls("http://127.0.0.1:5187");
builder.Services.AddSingleton(workspace);
builder.Services.AddSingleton<ICatalog, ManifestCatalog>();
builder.Services.AddSingleton<IJobRepository, FileJobRepository>();
builder.Services.AddSingleton<IJobQueue, InMemoryJobQueue>();
builder.Services.AddSingleton<ITryOnEngine, PythonTryOnEngine>();
builder.Services.AddSingleton<TryOnJobs>();
builder.Services.AddSingleton<RunTryOnJob>();
builder.Services.AddHostedService<TryOnWorker>();

var app = builder.Build();
app.Services.GetRequiredService<TryOnJobs>().RecoverInterruptedJobs();
app.UseDefaultFiles();
app.UseStaticFiles(new StaticFileOptions
{
    OnPrepareResponse = context => context.Context.Response.Headers.CacheControl = "no-store"
});
app.MapTryOnEndpoints();
app.Run();
