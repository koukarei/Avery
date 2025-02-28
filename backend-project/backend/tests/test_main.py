import os
import sys, asyncio
import datetime, time
import pytest
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient

from main import app 
from fastapi import UploadFile

client = TestClient(app)

def test_start_data():
    user_acc = {
        "username": os.getenv("ADMIN_USERNAME"),
        "email": os.getenv("ADMIN_EMAIL"),
        "password": os.getenv("ADMIN_PASSWORD"),
        "display_name": "Admin"
    }

    user_acc2 = {
        "username": os.getenv("USER_USERNAME"),
        "email": os.getenv("USER_EMAIL"),
        "password": os.getenv("USER_PASSWORD"),
        "display_name": "User"
    }

    response = client.post(
        "/sqlapp/users/", 
        json=user_acc.copy(), 
        headers={"Content-Type": "application/json"}
    )

    response = client.post(
        "/sqlapp/users/",
        json=user_acc2.copy(),
        headers={"Content-Type": "application/json"}
    )

@pytest.mark.usefixtures("login")
class TestAdmin:
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    _client = client

    def test_users(self):
        # Test read all users
        response = client.get(
            "/sqlapp/users/",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 200, response.json()
        
        new_user = {
            "username": "mary",
            "email": "mary@example.com",
            "password": "hogehoge",
            "display_name": "Mary"
        }

        # Test create a new user
        response = client.post("/sqlapp/users/", json=new_user.copy(),headers={"Content-Type": "application/json"})

        assert response.status_code == 201, response.json()
        assert response.json()['id'] > 0
        print(f'create a user {response.json()}')
        new_user_id = response.json()['id']

        # Test read a user
        response = client.get(
            f"/sqlapp/users/{new_user_id}",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 200, response.json()

        # Test read all users
        response = client.get(
            "/sqlapp/users/",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 200, response.json()
        assert len(response.json()) > 0
        num_users = len(response.json())

        # Test delete an unexisting user
        response = client.delete(
            f"/sqlapp/users/{new_user_id + 1}",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 404, response.json()

        # Test delete a user
        response = client.delete(
            f"/sqlapp/users/{new_user_id}",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 200, response.json()

        # Test read all users
        response = client.get(
            "/sqlapp/users/",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 200, response.json()
        assert len(response.json()) == num_users - 1   

    def test_read_scenes(self):
        
        # Test read all scenes
        response = client.get(
            "/sqlapp/scenes/",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 200, response.json()

        # Test create a new scene
        new_scene = {
            "name": "Beatrix Potter",
            "prompt": "in the style of Beatrix Potter"
        }

        response = client.post("/sqlapp/scene/", json=new_scene.copy(),headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 201, response.json()
        scene_id = response.json()['id']
        assert scene_id > 0

    def test_add_scenes(self):
        scenes = [
            {"name": "One Piece", "prompt": "in the style of One Piece"},
            {"name": "anime", "prompt": "in the style of anime"},
            {"name": "manga", "prompt": "in the style of manga"},
            {"name": "cartoon", "prompt": "in the style of cartoon"},
            {"name": "Simpsons", "prompt": "in the style of cartoon, the Simpsons"},
            {"name": "Disney", "prompt": "in the style of Disney"},
        ]

        for scene in scenes:
            response = client.post("/sqlapp/scene/", json=scene.copy(),headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"})
            assert response.status_code == 201, response.json()

    def test_add_programs(self):
        programs = [
            {
                "name": "inlab_test",
                "description": "For in-lab experiment. Link disclosed to LMS",
            },
            {
                "name": "haga_sensei_test",
                "description": "For Haga sensei trial version",
            },
            {
                "name": "student_january_experiment",
                "description": "For January experiment in Saikyo High School year 1",
            }
        ]

        for program in programs:
            response = client.post("/sqlapp/program", json=program.copy(),headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"})
            assert response.status_code == 201, response.json()

    def test_read_stories(self):

        # Test read all stories
        response = client.get("/sqlapp/stories/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200, response.json()
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
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
        print(f"story file uploaded: {response.json()}")
        assert response.status_code == 201, response.json()

        # Test whether story is created
        response = client.get("/sqlapp/stories/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200, response.json()
        assert len(response.json()) == num_stories + 1

    def test_add_guest_ac(self):
        response = client.get(
            f"/sqlapp/users",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        users = response.json()
        usernames = [user['username'] for user in users]
        for i in range(1,41):
            # Check if the guest account already exists
            if f"guest{i}" in usernames:
                continue
            
            guest_acc = {
                "username": f"guest{i}",
                "email": f"guest{i}@example.com",
                "password": "hogehoge",
                "display_name": f"Guest{i}"
            }

            response = client.post(
                "/sqlapp/users/",
                json=guest_acc.copy(),
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 201, response.json()

    def test_set_guest_ac_inactive(self):
        response = client.get("/sqlapp/users/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200, response.json()
        for user in response.json():
            if user['username'].startswith("guest"):
                user_update = {
                    'id': user['id'],
                    'is_active': False
                }
                response = client.put(
                    f"/sqlapp/users/{user['id']}",
                    json=user_update.copy(),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"}
                )
                assert response.status_code == 200, response.json()

    def test_set_guest_ac_active(self):
        response = client.get("/sqlapp/users/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200, response.json()
        for user in response.json():
            if user['username'].startswith("guest"):
                user_update = {
                    'id': user['id'],
                    'is_active': True
                }
                response = client.put(
                    f"/sqlapp/users/{user['id']}",
                    json=user_update.copy(),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"}
                )
                assert response.status_code == 200, response.json()


@pytest.mark.usefixtures("login")
class TestUser:
    _client = client
    
    def __init__(self, username, password):
        self.username = username
        self.password = password

    async def test_round(self):
        # Get leaderboard id
        response = client.get("/sqlapp/leaderboards/", headers={"Authorization": f"Bearer {self.access_token}"})
        if not response.json():
            assert False
        leaderboard = response.json()[0]
        leaderboard_id = leaderboard['id']

        # Test read all rounds for a leaderboard
        response = client.get(f"/sqlapp/leaderboards/{leaderboard_id}/rounds/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200, response.json()
        num_rounds = len(response.json())

        # Test create a new round
        new_round = {
            "leaderboard_id": leaderboard_id,
            "model": "gpt-4o-mini",
            "created_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        }

        response = client.post(
            f"/sqlapp/round/", 
            json=new_round.copy(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }
        )
        print(f"round created: {response.json()}")
        assert response.status_code == 200, response.json()
        round_id = response.json()['id']

        # Test read unfinish rounds for a leaderboard
        response = client.get(
            f"/sqlapp/unfinished_rounds/",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 200, response.json()
        assert len(response.json()) > 0

        # Test ask hint to chatbot
        new_message = {
            "content": "What should I do?",
            "created_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        }

        response = client.put(
            f"/sqlapp/round/{round_id}/chat",
            json=new_message.copy(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.access_token}"},
        )

        print(f"ask hint: {response.json()}")
        assert response.status_code == 200, response.json()

        new_generation = {
            "round_id": round_id,
            "created_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
            "generated_time": 1,
            "sentence": "The mouse set to work at once to carve the ham."
        }
        response = client.put(
            f"/sqlapp/round/{round_id}",
            json=new_generation.copy(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.access_token}"},
        )
        print(f"generation created: {response.json()}")
        assert response.status_code == 200, response.json()
        correct_sentence = response.json()['correct_sentence']
        generation_id = response.json()['id']

        interpretation_generation = {
            "id": generation_id,
            "correct_sentence": correct_sentence
        }

        # Test get interpretation
        response = client.put(
            f"/sqlapp/round/{round_id}/interpretation",
            json=interpretation_generation.copy(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.access_token}"},
        )
        print(f"Get interpretation: {response.json()}")
        assert response.status_code == 200, response.json()
        time.sleep(10)

        #Test get scores
        response = client.put(
            f"/sqlapp/round/{round_id}/complete",
            json={
                "id":generation_id,
                "at":datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
            },
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.access_token}"},
        )
        print(f"Complete generation: {response.json()}")
        assert response.status_code == 200, response.json()

        # Test complete round
        response = client.post(
            f"/sqlapp/round/{round_id}/end",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.access_token}"},
        )
        print(f"Complete round: {response.json()}")
        assert response.status_code == 200, response.json()

        # Test read all rounds for a leaderboard
        response = client.get(f"/sqlapp/leaderboards/{leaderboard_id}/rounds/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200, response.json()
        assert len(response.json()) == num_rounds + 1
    
    def test_chat(self):
        # Get leaderboard id
        response = client.get("/sqlapp/leaderboards/", headers={"Authorization": f"Bearer {self.access_token}"})
        if not response.json():
            return
        leaderboard = response.json()[0]
        leaderboard_id = leaderboard['id']

        # Get round id
        response = client.get(
            f"/sqlapp/leaderboards/{leaderboard_id}/rounds/",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        if not response.json():
            return
        thisround = response.json()[0]

        # Get chat
        response = client.get(
            f"/sqlapp/chat/{thisround['id']}",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 200, response.json()
        print(f"chat: {response.json()}")

    def test_image(self):

        # Get leaderboard id
        response = client.get(
            "/sqlapp/leaderboards/",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        if not response.json():
            assert False
        leaderboard = response.json()[0]
        leaderboard_id = leaderboard['id']

        # Get original image
        response = client.get(
            f"/sqlapp/original_image/{leaderboard_id}",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 200, response.json()

        # Get round id
        response = client.get(
            f"/sqlapp/leaderboards/{leaderboard_id}/rounds/",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 200, response.json()
        print(f"rounds: {response.json()}")
        
        generation_id = response.json()[0]['last_generation_id']

        # Get generated image
        response = client.get(
            f"/sqlapp/interpreted_image/{generation_id}",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 200, response.json()

def test_content_score():
    test_image_filename="cut_ham_for_test.jpg"

    with open(f"tests/{test_image_filename}", "rb") as f:
        response = client.post(
            "/sqlapp/content_score/",
            files={"image": (test_image_filename, f, "image/jpeg")},
            data={"sentence":"The mouse set to work at once to carve the ham."}
        )
    print(f"content score: {response.json()}")
    assert response.status_code == 200, response.json()

def test_vocabulary():
    pass
