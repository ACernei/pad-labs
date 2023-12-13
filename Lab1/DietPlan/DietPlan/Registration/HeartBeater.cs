using Grpc.Net.Client;
using Registration;
using DietPlan.Services;
using DietPlan.Services;
using RegistrationService = Registration.RegistrationService;

namespace DietPlan.Registration;

public sealed class HeartBeater : BackgroundService
{
    private readonly RegistrationService.RegistrationServiceClient client;
    private readonly IConfiguration configuration;
    private readonly LoadCounter counter;
    private readonly ILogger<HeartBeater> logger;

    public HeartBeater(
        RegistrationService.RegistrationServiceClient client,
        IConfiguration configuration,
        LoadCounter counter,
        ILogger<HeartBeater> logger)
    {
        this.client = client;
        this.configuration = configuration;
        this.counter = counter;
        this.logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var url = configuration.GetSection("Kestrel")
            .GetSection("Endpoints")
            .GetSection("gRPC")
            .GetValue<string>("Url");
        var uri = new Uri(url);
        var host = uri.GetComponents(UriComponents.Host, UriFormat.Unescaped);
        while (!stoppingToken.IsCancellationRequested)
        {
            //send heartbeat message
            client.UpdateServiceHeartbeat(new Heartbeat { ServiceName = "DietPlan", Host = host, Load = this.counter.GetLoad()});
            await Task.Delay(1000, stoppingToken);
        }
    }
}
