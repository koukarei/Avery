# Docker

## Create docker
```docker-compose build --no-cache```

## Run docker
```docker-compose up```

## Rebuild and run docker
```docker-compose down && docker-compose build --no-cache && docker-compose up -d```

## Rerun docker
```docker-compose down && docker-compose up -d```

## Stop specific container
```docker-compose rm -fsv react_front```

# Start Data

## Create User Account at start
```pytest tests/test_main.py::test_start_data```

## Add Scenes
```pytest tests/test_main.py::TestAdmin::test_add_scenes```

## Add Programs
```pytest tests/test_main.py::TestAdmin::test_add_programs```

## Add Story
```pytest tests/test_main.py::TestAdmin::test_read_stories```
