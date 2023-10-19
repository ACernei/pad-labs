using Grpc.Core;
using Grpc.Core.Interceptors;
using DietPlan.Services;
using DietPlan.Services;

namespace DietPlan.Interceptors;

public class LoadInterceptor: Interceptor
{
    private readonly LoadCounter counter;
    private readonly ILogger logger;

    public LoadInterceptor(
        LoadCounter counter,
        ILogger<LoadInterceptor> logger)
    {
        this.counter = counter;
        this.logger = logger;
    }

    public override async Task<TResponse> UnaryServerHandler<TRequest, TResponse>(
        TRequest request,
        ServerCallContext context,
        UnaryServerMethod<TRequest, TResponse> continuation)
    {
        logger.LogInformation("Starting receiving call. Type/Method: {Type} / {Method}",
            MethodType.Unary, context.Method);
        try
        {
            this.counter.Increase();
            var result = await continuation(request, context);
            this.counter.Decrease();
            return result;
        }
        catch (Exception ex)
        {
            this.counter.Decrease();
            logger.LogError(ex, $"Error thrown by {context.Method}.");
            throw;
        }
    }
}
