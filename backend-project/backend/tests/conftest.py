import pytest

@pytest.fixture(scope="class")
def login(request):

    username = request.cls.username
    password = request.cls.password
    print(f"Logging in with username: {username}")

    token_json = request.cls._client.post(
        "/sqlapp/token", data={"username": username, "password": password}
    )
    request.cls.access_token = token_json["access_token"]
    request.cls.refresh_token = token_json["refresh_token"]

    def logout():
        print("Logging out...")
        request.cls.access_token = None
        request.cls.refresh_token = None
    request.addfinalizer(logout)