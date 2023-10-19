using Registration;

namespace DietPlan.Registration;

public sealed class Deregister : BackgroundService
{
    private readonly RegistrationService.RegistrationServiceClient client;
    private readonly IConfiguration configuration;
    private readonly ILogger<Deregister> logger;

    public Deregister(
        RegistrationService.RegistrationServiceClient client,
        IConfiguration configuration,
        ILogger<Deregister> logger)
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
        while (!stoppingToken.IsCancellationRequested)
        {
            //send heartbeat message
            client.DeregisterService(new  DeregisterServiceRequest { Name = "DietPlan", Host = "0.0.0.0", Port = port });
            await Task.Delay(1000, stoppingToken);
        }
    }
}
