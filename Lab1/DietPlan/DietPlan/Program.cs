using DietPlan.Data;
using Microsoft.EntityFrameworkCore;
using DietPlan;
using DietPlan.Services;

var builder = WebApplication.CreateBuilder(args);

builder.WebHost.ConfigureKestrel(options =>
{
    options.Limits.MaxConcurrentConnections = 1;
    options.Limits.MaxConcurrentUpgradedConnections = 1;
});

builder.Services.AddGrpc();

builder.Services.AddDbContext<DietContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("DietContext")));

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var services = scope.ServiceProvider;

    var context = services.GetRequiredService<DietContext>();
    context.Database.EnsureCreated();
    context.Database.Migrate();
    // DbInitializer.Initialize(context);
}

app.MapGrpcService<DietCrudService>();
app.MapGrpcService<StatusService>();

app.MapGet("/",
    () =>
        "Communication with gRPC endpoints must be made through a gRPC client. To learn how to create a client, visit: https://go.microsoft.com/fwlink/?linkid=2086909");

app.Run();
