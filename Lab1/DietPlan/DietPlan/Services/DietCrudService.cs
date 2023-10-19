using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using DietPlan.Data;
using DietPlan.Mappers;

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
        diet.Id = Guid.NewGuid().ToString();
        diet.UserId = Guid.NewGuid().ToString();
        foreach (var food in diet.Foods)
        {
            food.Id = Guid.NewGuid().ToString();
        }

        this.context.Add(diet);
        await this.context.SaveChangesAsync();
        return new CreateDietResponse
        {
            Diet = Mapper.Map(diet),
        };
    }

    public override async Task<ReadDietResponse> ReadDiet(ReadDietRequest request, ServerCallContext context)
    {
        var diet = this.context.Diets.Include(x => x.Foods).FirstOrDefault(x => x.Id == request.DietId);
        await Task.Delay(1000);
        return new ReadDietResponse
        {
            Diet = Mapper.Map(diet),
        };
    }

    public override async Task<ReadAllDietsResponse> ReadAllDiets(ReadAllDietsRequest request, ServerCallContext context)
    {
        var diets = this.context.Diets.Include(x => x.Foods).Where(x => x.UserId == request.UserId).ToList();

        var response = new ReadAllDietsResponse();
        response.Diets.AddRange(diets.Select(Mapper.Map));
        return response;
    }

    public override async Task<UpdateDietResponse> UpdateDiet(UpdateDietRequest request, ServerCallContext context)
    {
        var existingDiet = this.context.Diets.Include(x => x.Foods).FirstOrDefault(x => x.Id == request.Diet.Id);
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
        var diet = this.context.Diets.Include(x => x.Foods).FirstOrDefault(x => x.Id == request.DietId);

        this.context.Foods.RemoveRange(diet.Foods);
        this.context.Remove(diet);
        await this.context.SaveChangesAsync();
        return new DeleteDietResponse
        {
            Message = "Diet deleted successfully"
        };
    }
}
