import os
import sys
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

        assert response.status_code == 200, response.json()
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
        assert response.status_code == 200, response.json()
        scene_id = response.json()['id']
        assert scene_id > 0

    def test_add_scenes(self):
        scenes = [
            {"name": "One Piece", "prompt": "in the style of One Piece"},
            {"name": "anime", "prompt": "in the style of anime"},
            {"name": "manga", "prompt": "in the style of manga"},
            {"name": "cartoon", "prompt": "in the style of cartoon"},
        ]

        for scene in scenes:
            response = client.post("/sqlapp/scene/", json=scene.copy(),headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"})
            assert response.status_code == 200, response.json()


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
        assert response.status_code == 200, response.json()

        # Test whether story is created
        response = client.get("/sqlapp/stories/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200, response.json()
        assert len(response.json()) == num_stories + 1

    def test_leaderboards(self):
        # Test read all leaderboards
        response = client.get(
            "/sqlapp/leaderboards/",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 200, response.json()
        
        num_leaderboards = len(response.json())
        
        #Get scene id
        response = client.get(
            "/sqlapp/scenes/",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        scene = response.json()[0]
        scene_id = scene['id']

        # Get story id
        response = client.get(
            "/sqlapp/stories/",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        story = response.json()[0]
        story_id = story['id']

        test_image_filename="cut_ham_for_test.jpg"
        test_image_path = "tests/{}".format(test_image_filename)

        # Test upload original image
        with open(test_image_path, "rb") as f:
            response = client.post(
                "/sqlapp/leaderboards/image/",
                files={"original_image": (test_image_filename, f, "image/jpeg")},
                headers={"Authorization": f"Bearer {self.access_token}"}
            )

        print(f"original image uploaded: {response.json()}")
        assert response.status_code == 200, response.json()
        original_image_id = response.json()['id']

        # Test create a new leaderboard
        new_leaderboard = {
            "title":"Cut the Ham",
            "story_extract": "The mouse set to work at once to carve the ham. It was a beautiful shiny yellow, streaked with red.",
            "is_public": True,
            "scene_id": scene_id,
            "story_id": story_id,
            "original_image_id": original_image_id,
        }

        response = client.post(
            "/sqlapp/leaderboards/", 
            json=new_leaderboard.copy(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"}
        )
        print(f"leaderboard created: {response.json()}")
        assert response.status_code == 200, response.json()

        # Test read all leaderboards
        response = client.get("/sqlapp/leaderboards/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200, response.json()
        assert len(response.json()) == num_leaderboards + 1

@pytest.mark.usefixtures("login")
class TestUser:
    username = os.getenv("USER_USERNAME")
    password = os.getenv("USER_PASSWORD")
    _client = client
    
    def test_round(self):
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
