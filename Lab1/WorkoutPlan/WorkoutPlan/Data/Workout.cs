namespace WorkoutPlan.Data;

public class Workout
{
    public string? Id { get; set; }
    public string? UserId { get; set; }
    public string? Name { get; set; }
    public string? Description { get; set; }
    public List<Exercise>? Exercises { get; set; }

    public void Update(Workout other)
    {
        UserId = other.UserId;
        Name = other.Name;
        Description = other.Description;
        Exercises = other.Exercises;
    }
}
