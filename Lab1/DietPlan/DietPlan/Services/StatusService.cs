using Grpc.Core;

namespace DietPlan.Services;

public class StatusService : Status.StatusBase
{
    private readonly ILogger<StatusService> logger;

    public StatusService(ILogger<StatusService> logger)
    {
        this.logger = logger;
    }

    public override async Task<GetStatusResponse> GetStatus(GetStatusRequest request, ServerCallContext context)
    {
        await Task.Delay(3000);

        return new GetStatusResponse
        {
            Status = "Service is up and running"
        };
    }
}
