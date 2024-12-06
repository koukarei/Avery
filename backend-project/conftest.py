import pytest

@pytest.fixture(scope="class")
def login(request):

    username = request.cls.username
    password = request.cls.password
    print(f"Logging in with username: {username}")

    def logout():
        print("Logging out...")
    request.addfinalizer(logout)