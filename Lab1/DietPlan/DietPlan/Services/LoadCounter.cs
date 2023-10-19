namespace DietPlan.Services;

public class LoadCounter
{
    private int load = 0;

    public void Increase() => Interlocked.Increment(ref this.load);

    public void Decrease() => Interlocked.Decrement(ref this.load);
    public int GetLoad() => load;
}
