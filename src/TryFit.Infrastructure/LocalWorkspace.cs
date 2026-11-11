namespace TryFit.Infrastructure;

public sealed class LocalWorkspace(string root)
{
    public string Root { get; } = Path.GetFullPath(root);
    public string JobsDirectory => Path.Combine(Root, "runs", "local-jobs");
    public string Python => Path.Combine(Root, ".venv", OperatingSystem.IsWindows() ? "Scripts/python.exe" : "bin/python");

    internal string JobDirectory(Guid id) => Path.Combine(JobsDirectory, id.ToString("N"));
}
