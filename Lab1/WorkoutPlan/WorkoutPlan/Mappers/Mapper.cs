namespace WorkoutPlan.Mappers;

public static class Mapper
{
    public static WorkoutPlan.Data.Workout Map(Workout source) => new()
    {
        Id = source.Id,
        UserId = source.UserId,
        Name = source.Name,
        Description = source.Description,
        Exercises = source.Exercises.Select(Map).ToList(),
    };

    public static WorkoutPlan.Data.Exercise Map(Exercise source) => new()
    {
        Id = source.Id,
        Name = source.Name,
        Description = source.Description,
        Sets = source.Sets,
        Repetitions = source.Repetitions,
    };

    public static Workout Map(WorkoutPlan.Data.Workout source)
    {
        var workout = new Workout
        {
            Id = source.Id,
            UserId = source.UserId,
            Name = source.Name,
            Description = source.Description,
        };
        workout.Exercises.AddRange(source.Exercises.Select(Mapper.Map));
        return workout;
    }

    public static Exercise Map(WorkoutPlan.Data.Exercise source) => new()
    {
        Id = source.Id,
        Name = source.Name,
        Description = source.Description,
        Sets = source.Sets,
        Repetitions = source.Repetitions,
    };
}
