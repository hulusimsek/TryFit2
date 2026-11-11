using System.Threading.Channels;
using TryFit.Application;

namespace TryFit.Infrastructure;

public sealed class InMemoryJobQueue : IJobQueue
{
    private readonly Channel<Guid> channel = Channel.CreateUnbounded<Guid>(
        new UnboundedChannelOptions { SingleReader = true });

    public void Enqueue(Guid id)
    {
        if (!channel.Writer.TryWrite(id))
            throw new InvalidOperationException("The local job queue is closed.");
    }

    public IAsyncEnumerable<Guid> ReadAllAsync(CancellationToken cancellationToken) =>
        channel.Reader.ReadAllAsync(cancellationToken);
}
