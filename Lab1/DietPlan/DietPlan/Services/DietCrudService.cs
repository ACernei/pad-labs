using DietPlan.Data;
using DietPlan.Mappers;
using Grpc.Core;

namespace DietPlan.Services;

public class DietCrudService : DietCrud.DietCrudBase
{
    private readonly DietContext context;
    private readonly ILogger<DietCrudService> logger;

    public DietCrudService(
        DietContext context,
        ILogger<DietCrudService> logger)
    {
        this.context = context;
        this.logger = logger;
    }

    public override async Task<CreateDietResponse> CreateDiet(CreateDietRequest request, ServerCallContext context)
    {
        var diet = Mapper.Map(request.Diet);
        this.context.Add(diet);
        await this.context.SaveChangesAsync();
        return new CreateDietResponse
        {
            Diet = Mapper.Map(diet),
        };
    }

    public override async Task<ReadDietResponse> ReadDiet(ReadDietRequest request, ServerCallContext context)
    {
        var diet = this.context.Diets.FirstOrDefault(x => x.Id == request.DietId);
        return new ReadDietResponse
        {
            Diet = Mapper.Map(diet),
        };
    }

    public override async Task<ReadAllDietsResponse> ReadAllDiets(ReadAllDietsRequest request, ServerCallContext context)
    {
        var diets = this.context.Diets.Where(x => x.UserId == request.UserId).ToList();

        var response = new ReadAllDietsResponse();
        response.Diets.AddRange(diets.Select(Mapper.Map));
        return response;
    }

    public override async Task<UpdateDietResponse> UpdateDiet(UpdateDietRequest request, ServerCallContext context)
    {
        var existingDiet = this.context.Diets.FirstOrDefault(x => x.Id == request.Diet.Id);
        var diet = Mapper.Map(request.Diet);
        existingDiet.Update(diet);

        await this.context.SaveChangesAsync();
        return new UpdateDietResponse
        {
            Diet = Mapper.Map(existingDiet),
        };
    }

    public override async Task<DeleteDietResponse> DeleteDiet(DeleteDietRequest request, ServerCallContext context)
    {
        var diet = this.context.Diets.FirstOrDefault(x => x.Id == request.DietId);

        // var diet = Mapper.Map(request.Diet);
        this.context.Remove(diet);
        await this.context.SaveChangesAsync();
        return new DeleteDietResponse
        {
            Message = "Diet deleted successfully"
        };
    }
}
