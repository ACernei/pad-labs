using Registration;

namespace WorkoutPlan.Registration;

public sealed class Register : BackgroundService
{
    private readonly RegistrationService.RegistrationServiceClient client;
    private readonly IConfiguration configuration;
    private readonly ILogger<Register> logger;

    public Register(
        RegistrationService.RegistrationServiceClient client,
        IConfiguration configuration,
        ILogger<Register> logger)
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
        var host = uri.GetComponents(UriComponents.Host, UriFormat.Unescaped);
        var port = int.Parse(uri.GetComponents(UriComponents.Port, UriFormat.Unescaped));
        while (!stoppingToken.IsCancellationRequested)
        {
            //send heartbeat message
            client.RegisterService(new ServiceRegistration { Name = "WorkoutPlan", Host = host, Port = port });
            await Task.Delay(1000, stoppingToken);
        }
    }
}
