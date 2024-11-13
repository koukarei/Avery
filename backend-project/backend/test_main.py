import os
import sys
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient

from main import app 

client = TestClient(app)


def test_users():
    # Test read all users
    response = client.get("/sqlapp/users/")
    assert response.status_code == 200
    new_user = {
        "username": "mary",
        "email": "mary@example.com",
        "password": "hogehoge",
        "display_name": "Mary"
    }

    # Test create a new user
    response = client.post("/sqlapp/users/", json=new_user.copy(),headers={"Content-Type": "application/json"})

    assert response.status_code == 200
    assert response.json()['id'] > 0
    print(f'create a user {response.json()}')
    new_user_id = response.json()['id']

    # Test read a user
    response = client.get(f"/sqlapp/users/{new_user_id}")
    assert response.status_code == 200

    # Test read all users
    response = client.get("/sqlapp/users/")
    assert response.status_code == 200
    assert len(response.json()) > 0
    num_users = len(response.json())

    # Test delete an unexisting user
    response = client.delete(f"/sqlapp/users/{new_user_id + 1}")
    assert response.status_code == 404

    # Test delete a user
    response = client.delete(f"/sqlapp/users/{new_user_id}")
    assert response.status_code == 200

    # Test read all users
    response = client.get("/sqlapp/users/")
    assert response.status_code == 200
    assert len(response.json()) == num_users - 1   

    if 'admin' not in [i['username'] for i in response.json()]:
        admin_user = {
            "username": "admin",
            "email": "admin@example.com",
            "password": "hogehoge",
            "display_name": "Admin"
        }
        response = client.post("/sqlapp/users/", json=admin_user.copy(),headers={"Content-Type": "application/json"})


def test_read_scenes():
    response = client.get("/sqlapp/scenes/")
    assert response.status_code == 200

def test_read_stories():
    response = client.get("/sqlapp/stories/")
    assert response.status_code == 200

def test_read_leaderboards():
    response = client.get("/sqlapp/leaderboards/")
    assert response.status_code == 200




