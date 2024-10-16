from fastapi.testclient import TestClient

from .main import app 

client = TestClient(app)


def test_read_users():
    response = client.get("/sqlapp/users/")
    assert response.status_code == 200

def test_read_scenes():
    response = client.get("/sqlapp/scenes/")
    assert response.status_code == 200

def test_read_stories():
    response = client.get("/sqlapp/stories/")
    assert response.status_code == 200

def test_read_leaderboards():
    response = client.get("/sqlapp/leaderboards/")
    assert response.status_code == 200

