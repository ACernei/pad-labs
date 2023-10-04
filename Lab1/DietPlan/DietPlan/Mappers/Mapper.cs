namespace DietPlan.Mappers;

public static class Mapper
{
    public static DietPlan.Data.Diet Map(Diet source) => new()
    {
        Id = source.Id,
        UserId = source.UserId,
        Name = source.Name,
        Description = source.Description,
        Foods = source.Foods.Select(Map).ToList(),
    };

    public static DietPlan.Data.Food Map(Food source) => new()
    {
        Id = source.Id,
        Name = source.Name,
        Description = source.Description,
        Calories = source.Calories,
        Repetitions = source.Repetitions,
    };

    public static Diet Map(DietPlan.Data.Diet source)
    {
        var diet = new Diet
        {
            Id = source.Id,
            UserId = source.UserId,
            Name = source.Name,
            Description = source.Description,
        };
        diet.Foods.AddRange(source.Foods.Select(Mapper.Map));
        return diet;
    }

    public static Food Map(DietPlan.Data.Food source) => new()
    {
        Id = source.Id,
        Name = source.Name,
        Description = source.Description,
        Calories = source.Calories,
        Repetitions = source.Repetitions,
    };
}
