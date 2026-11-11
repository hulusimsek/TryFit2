using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using TryFit.Application;
using TryFit.Domain;

namespace TryFit.Infrastructure;

public sealed class PythonTryOnEngine(LocalWorkspace workspace) : ITryOnEngine
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web) { WriteIndented = true };
    private static readonly byte[] PngSignature = [137, 80, 78, 71, 13, 10, 26, 10];
    private const int MaximumLogLength = 100_000;

    public bool IsReady => File.Exists(workspace.Python);

    public async Task GenerateAsync(TryFitJob job, Action<TryOnStage> reportStage, CancellationToken cancellationToken)
    {
        var directory = workspace.JobDirectory(job.Id);
        File.WriteAllText(Path.Combine(directory, "request.json"), JsonSerializer.Serialize(job.Selection, Json));

        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(TimeSpan.FromMinutes(10));
        using var process = new Process { StartInfo = BuildStartInfo(directory) };
        var log = new StringBuilder();
        var logLock = new object();
        TryOnStage? lastStage = null;

        async Task ReadOutputAsync(StreamReader reader)
        {
            while (await reader.ReadLineAsync(deadline.Token) is { } line)
            {
                lock (logLock)
                {
                    if (log.Length < MaximumLogLength)
                        log.AppendLine(line);

                    if (lastStage != TryOnStage.Lower && line.Contains("TOP_COMPLETED", StringComparison.Ordinal))
                    {
                        lastStage = TryOnStage.Lower;
                        reportStage(TryOnStage.Lower);
                    }
                    else if (lastStage is null && line.Contains("Running inference", StringComparison.Ordinal))
                    {
                        lastStage = TryOnStage.Upper;
                        reportStage(TryOnStage.Upper);
                    }
                }
            }
        }

        var started = false;
        try
        {
            cancellationToken.ThrowIfCancellationRequested();
            started = process.Start();
            if (!started)
                throw new InvalidOperationException("Python süreci başlatılamadı.");

            await Task.WhenAll(
                process.WaitForExitAsync(deadline.Token),
                ReadOutputAsync(process.StandardOutput),
                ReadOutputAsync(process.StandardError));

            if (process.ExitCode != 0)
                throw new InvalidOperationException("Python üretimi tamamlanamadı.");

            VerifyOutput(directory);
        }
        finally
        {
            if (started && !process.HasExited)
            {
                try
                {
                    process.Kill(entireProcessTree: true);
                }
                catch (InvalidOperationException) when (process.HasExited)
                {
                    // The process exited between the check and Kill.
                }
                await process.WaitForExitAsync();
            }

            File.WriteAllText(Path.Combine(directory, "worker.log"), log.ToString());
        }
    }

    private ProcessStartInfo BuildStartInfo(string directory)
    {
        var start = new ProcessStartInfo(workspace.Python)
        {
            WorkingDirectory = workspace.Root,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        start.ArgumentList.Add("-u");
        start.ArgumentList.Add(Path.Combine(workspace.Root, "ai-worker", "app", "local_job.py"));
        start.ArgumentList.Add("--job-dir");
        start.ArgumentList.Add(directory);
        start.Environment["HF_HUB_OFFLINE"] = "1";
        start.Environment["TRANSFORMERS_OFFLINE"] = "1";
        start.Environment["HF_HOME"] = Path.Combine(workspace.Root, "ai-worker", "models", "hf-cache");
        start.Environment["MPLCONFIGDIR"] = Path.Combine(workspace.Root, ".venv", "matplotlib");
        start.Environment["OMP_NUM_THREADS"] = "8";
        return start;
    }

    private static void VerifyOutput(string directory)
    {
        using var outcome = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "outcome.json")));
        using var png = File.OpenRead(Path.Combine(directory, "result.png"));
        var signature = new byte[PngSignature.Length];
        png.ReadExactly(signature);
        png.Position = 0;

        if (outcome.RootElement.GetProperty("status").GetString() != "completed"
            || !signature.AsSpan().SequenceEqual(PngSignature)
            || !Convert.ToHexString(SHA256.HashData(png)).Equals(
                outcome.RootElement.GetProperty("outputSha256").GetString(), StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidDataException("Gerçek çıktı dosyası doğrulanamadı.");
        }
    }
}
