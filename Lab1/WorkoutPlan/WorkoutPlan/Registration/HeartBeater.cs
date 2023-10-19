using Grpc.Net.Client;
using Registration;
using WorkoutPlan.Services;
using RegistrationService = Registration.RegistrationService;

namespace WorkoutPlan.Registration;

public sealed class HeartBeater : BackgroundService
{
    private readonly RegistrationService.RegistrationServiceClient client;
    private readonly IConfiguration configuration;
    private readonly ILogger<HeartBeater> logger;

    public HeartBeater(
        RegistrationService.RegistrationServiceClient client,
        IConfiguration configuration,
        ILogger<HeartBeater> logger)
    {
        this.client = client;
        this.configuration = configuration;
        this.logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var url = configuration.GetSection("Kestrel")
            .GetSection("Endpoints")
            .GetSection("gRPC")
            .GetValue<string>("Url");
        var uri = new Uri(url);
        var port = int.Parse(uri.GetComponents(UriComponents.Port, UriFormat.Unescaped));
        var load = 0;
        while (!stoppingToken.IsCancellationRequested)
        {
            //send heartbeat message
            client.UpdateServiceHeartbeat(new Heartbeat { ServiceName = "WorkoutPlan", Port = port, Load = load});
            await Task.Delay(1000, stoppingToken);
        }
    }
}
