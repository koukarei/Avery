# Create docker
```docker-compose build --no-cache```

# Run docker
```docker-compose up```

# Rebuild and run docker
```docker-compose down && docker-compose build --no-cache && docker-compose up -d```

# Rerun docker
```docker-compose down && docker-compose up -d```

# Stop specific container
```docker-compose rm -fsv react_front```