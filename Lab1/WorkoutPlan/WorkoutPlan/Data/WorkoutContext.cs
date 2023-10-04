using Microsoft.EntityFrameworkCore;

namespace WorkoutPlan.Data;

public class WorkoutContext : DbContext
{
    public WorkoutContext(DbContextOptions<WorkoutContext> options)
        : base(options)
    {
    }

    public DbSet<Workout>? Workouts { get; set; }
    public DbSet<Exercise>? Exercises { get; set; }
}
