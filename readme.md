# Create docker
docker build -t avery-app .

# Run docker
docker run -dp 127.0.0.1:3100:7860 avery-app

