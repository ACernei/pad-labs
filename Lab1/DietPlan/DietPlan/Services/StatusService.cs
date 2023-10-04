using Grpc.Core;

namespace DietPlan.Services;

public class StatusService : Status.StatusBase
{
    private readonly ILogger<StatusService> _logger;

    public StatusService(ILogger<StatusService> logger)
    {
        _logger = logger;
    }

    public override Task<GetStatusResponse> GetStatus(GetStatusRequest request, ServerCallContext context)
    {
        return Task.FromResult(new GetStatusResponse
        {
            Status = "Service is up and running"
        });
    }
}
