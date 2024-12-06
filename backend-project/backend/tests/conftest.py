import pytest

@pytest.fixture(scope="class")
def login(request):

    username = request.cls.username
    password = request.cls.password
    print(f"Logging in with username: {username}")

    token_json = request.cls._client.post(
        "/sqlapp/token", data={"username": username, "password": password}
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