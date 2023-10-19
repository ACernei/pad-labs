using Microsoft.EntityFrameworkCore;
using WorkoutPlan;
using WorkoutPlan.Data;
using WorkoutPlan.Interceptors;
using WorkoutPlan.Registration;
using WorkoutPlan.Services;
using RegistrationService = Registration.RegistrationService;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddGrpc(options =>
{
    options.Interceptors.Add<LoadInterceptor>();
});
builder.Services
    .AddGrpcClient<RegistrationService.RegistrationServiceClient>(o =>
    {
        o.Address = new Uri(builder.Configuration.GetValue<string>("ServiceDiscoveryUrl"));
    })
    .ConfigurePrimaryHttpMessageHandler(() =>
    {
        var handler = new HttpClientHandler();
        handler.ServerCertificateCustomValidationCallback = HttpClientHandler.DangerousAcceptAnyServerCertificateValidator;
        return handler;
    });

builder.Services.AddHostedService<Register>();
builder.Services.AddHostedService<HeartBeater>();
builder.Services.AddSingleton<LoadCounter>();

builder.Services.AddDbContext<WorkoutContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("WorkoutContext")));

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var services = scope.ServiceProvider;

    var context = services.GetRequiredService<WorkoutContext>();
    context.Database.Migrate();
}

app.MapGrpcService<WorkoutCrudService>();
app.MapGrpcService<StatusService>();

app.MapGet("/",
    () =>
        "Communication with gRPC endpoints must be made through a gRPC client. To learn how to create a client, visit: https://go.microsoft.com/fwlink/?linkid=2086909");

app.Run();
