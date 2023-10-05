using Grpc.Core;

namespace WorkoutPlan.Services;

public class StatusService : Status.StatusBase
{
    private readonly ILogger<StatusService> logger;

    public StatusService(ILogger<StatusService> logger)
    {
        this.logger = logger;
    }

    public override Task<GetStatusResponse> GetStatus(GetStatusRequest request, ServerCallContext context)
    {
        return Task.FromResult(new GetStatusResponse
        {
            Status = "Service is up and running"
        });
    }
}
