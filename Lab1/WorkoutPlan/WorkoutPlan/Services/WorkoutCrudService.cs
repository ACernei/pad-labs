using Grpc.Core;
using WorkoutPlan.Data;
using WorkoutPlan.Mappers;

namespace WorkoutPlan.Services;

public class WorkoutCrudService : WorkoutCrud.WorkoutCrudBase
{
    private readonly WorkoutContext context;
    private readonly ILogger<WorkoutCrudService> logger;

    public WorkoutCrudService(
        WorkoutContext context,
        ILogger<WorkoutCrudService> logger)
    {
        this.context = context;
        this.logger = logger;
    }

    public override async Task<CreateWorkoutResponse> CreateWorkout(CreateWorkoutRequest request, ServerCallContext context)
    {
        var workout = Mapper.Map(request.Workout);
        this.context.Add(workout);
        await this.context.SaveChangesAsync();
        return new CreateWorkoutResponse
        {
            Workout = Mapper.Map(workout),
        };
    }

    public override async Task<ReadWorkoutResponse> ReadWorkout(ReadWorkoutRequest request, ServerCallContext context)
    {
        var workout = this.context.Workouts.FirstOrDefault(x => x.Id == request.WorkoutId);
        return new ReadWorkoutResponse
        {
            Workout = Mapper.Map(workout),
        };
    }

    public override async Task<ReadAllWorkoutsResponse> ReadAllWorkouts(ReadAllWorkoutsRequest request, ServerCallContext context)
    {
        var workouts = this.context.Workouts.Where(x => x.UserId == request.UserId).ToList();

        var response = new ReadAllWorkoutsResponse();
        response.Workouts.AddRange(workouts.Select(Mapper.Map));
        return response;
    }

    public override async Task<UpdateWorkoutResponse> UpdateWorkout(UpdateWorkoutRequest request, ServerCallContext context)
    {
        var existingWorkout = this.context.Workouts.FirstOrDefault(x => x.Id == request.Workout.Id);
        var workout = Mapper.Map(request.Workout);
        existingWorkout.Update(workout);

        await this.context.SaveChangesAsync();
        return new UpdateWorkoutResponse
        {
            Workout = Mapper.Map(existingWorkout),
        };
    }

    public override async Task<DeleteWorkoutResponse> DeleteWorkout(DeleteWorkoutRequest request, ServerCallContext context)
    {
        var workout = this.context.Workouts.FirstOrDefault(x => x.Id == request.WorkoutId);

        // var workout = Mapper.Map(request.Workout);
        this.context.Remove(workout);
        await this.context.SaveChangesAsync();
        return new DeleteWorkoutResponse
        {
            Message = "Workout deleted successfully"
        };
    }
}
