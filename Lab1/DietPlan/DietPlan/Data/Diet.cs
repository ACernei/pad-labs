namespace DietPlan.Data;

public class Diet
{
    public string? Id { get; set; }
    public string? UserId { get; set; }
    public string? Name { get; set; }
    public string? Description { get; set; }
    public List<Food>? Foods { get; set; }

    public void Update(Diet other)
    {
        UserId = other.UserId;
        Name = other.Name;
        Description = other.Description;
        Foods = other.Foods;
    }
}
