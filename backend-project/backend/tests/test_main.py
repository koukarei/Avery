import os
import sys
import datetime
import time
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient

from main import app 
from fastapi import UploadFile

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
    # Test read all scenes
    response = client.get("/sqlapp/scenes/")
    assert response.status_code == 200

    # Test create a new scene
    new_scene = {
        "name": "Beatrix Potter",
        "prompt": "in the style of Beatrix Potter"
    }

    response = client.post("/sqlapp/scene/", json=new_scene.copy(),headers={"Content-Type": "application/json"})
    assert response.status_code == 200
    scene_id = response.json()['id']
    assert scene_id > 0

def test_read_stories():
    # Test read all stories
    response = client.get("/sqlapp/stories/")
    assert response.status_code == 200
    num_stories = len(response.json())

    # Test create a new story
    test_file_path = "tests/mice_story_for_test.txt"
    with open(test_file_path, "rb") as f:
        response = client.post(
            "/sqlapp/story/",
            files={"story_content_file": ("mice_story_for_test.txt", f, "text/plain")},
            data={
                "title": "The Tale of Two Bad Mice",
                "scene_id": "1"  
            },
        )
    print(f"story file uploaded: {response.json()}")
    assert response.status_code == 200

    # Test whether story is created
    response = client.get("/sqlapp/stories/")
    assert response.status_code == 200
    assert len(response.json()) == num_stories + 1

def test_leaderboards():
    # Test read all leaderboards
    response = client.get("/sqlapp/leaderboards/")
    assert response.status_code == 200
    
    num_leaderboards = len(response.json())

    # Get user id
    response = client.get("/sqlapp/users/")
    user = response.json()[0]
    user_id = user['id']

    #Get scene id
    response = client.get("/sqlapp/scenes/")
    scene = response.json()[0]
    scene_id = scene['id']

    # Get story id
    response = client.get("/sqlapp/stories/")
    story = response.json()[0]
    story_id = story['id']

    test_image_filename="cut_ham_for_test.jpg"
    test_image_path = "tests/{}".format(test_image_filename)

    # Test upload original image
    with open(test_image_path, "rb") as f:
        response = client.post(
            "/sqlapp/leaderboards/image/",
            files={"original_image": (test_image_filename, f, "image/jpeg")},
        )

    print(f"original image uploaded: {response.json()}")
    assert response.status_code == 200
    original_image_id = response.json()['id']

    # Test create a new leaderboard
    new_leaderboard = {
        "title":"Cut the Ham",
        "story_extract": "The mouse set to work at once to carve the ham. It was a beautiful shiny yellow, streaked with red.",
        "is_public": True,
        "scene_id": scene_id,
        "story_id": story_id,
        "original_image_id": original_image_id,
        "created_by_id": user_id,
    }

    response = client.post("/sqlapp/leaderboards/", json=new_leaderboard.copy(),headers={"Content-Type": "application/json"})
    print(f"leaderboard created: {response.json()}")
    assert response.status_code == 200

    # Test read all leaderboards
    response = client.get("/sqlapp/leaderboards/")
    assert response.status_code == 200
    assert len(response.json()) == num_leaderboards + 1

def test_round():
    # Get leaderboard id
    response = client.get("/sqlapp/leaderboards/")
    if not response.json():
        assert False
    leaderboard = response.json()[0]
    leaderboard_id = leaderboard['id']

    # Test read all rounds for a leaderboard
    response = client.get(f"/sqlapp/leaderboards/{leaderboard_id}/rounds/")
    assert response.status_code == 200
    num_rounds = len(response.json())

    # Get user id
    response = client.get("/sqlapp/users/")
    user = response.json()[0]
    user_id = user['id']

    # Test create a new round
    new_round = {
        "leaderboard_id": leaderboard_id,
        "model": "gpt-4o-mini",
        "created_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
    }
    data_json = {
        "thisround":new_round.copy(),
        "player_id":user_id
    }
    response = client.post("/sqlapp/users/", json=data_json,headers={"Content-Type": "application/json"})
    print(f"round created: {response.json()}")
    assert response.status_code == 200

    # Test read all rounds for a leaderboard
    response = client.get(f"/sqlapp/leaderboards/{leaderboard_id}/rounds/")
    assert response.status_code == 200
    assert len(response.json()) == num_rounds + 1

    # Answer
    round_id = response.json()[0]['id']

    new_generation = {
        "round_id": round_id,
        "created_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        "generated_time": 1,
        "sentence": "The mouse set to work at once to carve the ham."
    }
    response = client.put(
        f"/sqlapp/round/{round_id}",
        json=new_generation.copy(),
        headers={"Content-Type": "application/json"},
    )
    print(f"generation created: {response.json()}")
    assert response.status_code == 200
    correct_sentence = response.json()['correct_sentence']
    generation_id = response.json()['id']

    # Test get interpretation
    response = client.put(
        f"/sqlapp/round/{round_id}/interpretation",
        json={
            "round_id": round_id,
            "generation": {
                "id": generation_id,
                "correct_sentence": correct_sentence
            }
        },
        headers={"Content-Type": "application/json"},
    )
    print(f"Get interpretation: {response.json()}")
    assert response.status_code == 200
    time.sleep(10)

    #Test get scores
    response = client.put(
        f"/sqlapp/round/{round_id}/complete",
        json={
            "id":generation_id,
            "at":datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        },
        headers={"Content-Type": "application/json"},
    )
    print(f"Complete generation: {response.json()}")
    assert response.status_code == 200

    # Test complete round
    response = client.post(
        f"/round/{round_id}/end",
        headers={"Content-Type": "application/json"},
    )
    print(f"Complete round: {response.json()}")
    assert response.status_code == 200

    # Test read all rounds for a leaderboard
    response = client.get(f"/sqlapp/leaderboards/{leaderboard_id}/rounds/")
    assert response.status_code == 200
    assert len(response.json()) == num_rounds + 1

def test_vocabulary():
    pass

def test_chat():
    pass

def test_image():
    pass


