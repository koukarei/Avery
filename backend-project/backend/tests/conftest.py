import pytest, httpx

@pytest.fixture(scope="class")
def login(request):

    username = request.cls.username
    password = request.cls.password
    print(f"Logging in with username: {username}")

    token_json = request.cls._client.post(
        "/sqlapp2/token", data={"username": username, "password": password}
    )
    assert token_json.status_code == 200
    assert 'access_token' in token_json.json()
    assert 'refresh_token' in token_json.json()
    
    request.cls.access_token = token_json.json()["access_token"]
    request.cls.refresh_token = token_json.json()["refresh_token"]

    def logout():
        print("Logging out...")
        request.cls.access_token = None
        request.cls.refresh_token = None
    request.addfinalizer(logout)

    return request.cls.access_token

@pytest.fixture(scope="class")
def login_guest(request):
    username = request.node.get_closest_marker('username').args[0] if request.node.get_closest_marker('username') else request.cls.username
    password = request.node.get_closest_marker('password').args[0] if request.node.get_closest_marker('password') else request.cls.password

    print(f"Logging in with username: {username}")

    token_json = request.cls._client.post(
        "/sqlapp2/token", data={"username": username, "password": password}
    )
    assert token_json.status_code == 200
    assert 'access_token' in token_json.json()
    assert 'refresh_token' in token_json.json()
    
    # Directly set access_token and refresh_token on the instance
    request.cls.access_token = token_json.json()["access_token"]
    request.cls.refresh_token = token_json.json()["refresh_token"]

    def logout():
        print("Logging out...")
        request.cls.access_token = None
        request.cls.refresh_token = None
    request.addfinalizer(logout)

    return request.cls.access_token

# Configure the default asyncio loop scope
@pytest.fixture(scope="class")
def asyncio_default_loop_scope():
    """Sets the asyncio default event loop scope."""
    return "class"  # Change to "function", "class", "module", or "session" as needed

# Timer for each test function
@pytest.fixture(autouse=True, scope="function")
def timer():
    import time
    start_time = time.time()
    yield
    end_time = time.time()
    print(f"Test function took {end_time - start_time:.2f} seconds")