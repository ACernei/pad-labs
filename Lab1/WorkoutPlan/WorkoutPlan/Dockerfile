FROM mcr.microsoft.com/dotnet/aspnet:7.0 AS base
WORKDIR /app

FROM mcr.microsoft.com/dotnet/sdk:7.0 AS build
WORKDIR /src
COPY ["WorkoutPlan.csproj", "WorkoutPlan/"]
RUN dotnet restore "WorkoutPlan/WorkoutPlan.csproj"
COPY . "WorkoutPlan/"
WORKDIR "/src/WorkoutPlan"
RUN dotnet build "WorkoutPlan.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "WorkoutPlan.csproj" -c Release -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "WorkoutPlan.dll"]
