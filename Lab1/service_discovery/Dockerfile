# Use the official Python image as the base image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the entire current directory into the container
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt


# Expose the port your service will run on
EXPOSE 5001

# Run your Python script
CMD ["python", "main.py"]