using Microsoft.EntityFrameworkCore;

namespace DietPlan.Data;

public class DietContext : DbContext
{
    public DietContext(DbContextOptions<DietContext> options)
        : base(options)
    {
    }

    public DbSet<DietPlan.Data.Diet>? Diets { get; set; }
    public DbSet<DietPlan.Data.Food>? Foods { get; set; }
}
