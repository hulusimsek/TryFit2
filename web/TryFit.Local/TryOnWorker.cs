using TryFit.Application;

namespace TryFit.Local;

internal sealed class TryOnWorker(
    IJobQueue queue, RunTryOnJob runJob, ILogger<TryOnWorker> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await foreach (var id in queue.ReadAllAsync(stoppingToken))
        {
            if (stoppingToken.IsCancellationRequested)
                break;

            try
            {
                await runJob.ExecuteAsync(id, stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception error)
            {
                logger.LogWarning(error, "Local try-on job {JobId} failed", id);
            }
        }
    }
}
