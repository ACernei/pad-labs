using Microsoft.EntityFrameworkCore;
using WorkoutPlan;
using WorkoutPlan.Data;
using WorkoutPlan.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddGrpc();

builder.Services.AddDbContext<WorkoutContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("WorkoutContext")));

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var services = scope.ServiceProvider;

    var context = services.GetRequiredService<WorkoutContext>();
    context.Database.EnsureCreated();
    context.Database.Migrate();
}

app.MapGrpcService<WorkoutCrudService>();
app.MapGrpcService<StatusService>();

app.MapGet("/",
    () =>
        "Communication with gRPC endpoints must be made through a gRPC client. To learn how to create a client, visit: https://go.microsoft.com/fwlink/?linkid=2086909");

app.Run();
