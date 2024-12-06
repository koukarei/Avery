import os
import sys
import datetime
import time
sys.path.append(os.getcwd())
import csv

from fastapi.testclient import TestClient

from main import app 
from fastapi import UploadFile
import pytest

client = TestClient(app)

@pytest.mark.usefixtures("login")
class TestPlay:
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    _client = client

    def test_play(self):
        # Create leaderboards
        response = client.post(
            "/sqlapp/leaderboards/create",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )

        picture_dir = 'initial/pic/'

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

        leaderboard_dict = {}

        for filename in os.listdir(picture_dir):
            image_path = picture_dir+'/'+filename

            # Test upload original image
            with open(image_path, "rb") as f:
                response = client.post(
                    "/sqlapp/leaderboards/image/",
                    files={"original_image": (filename, f, "image/jpeg")},
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )

            assert response.status_code == 200
            original_image_id = response.json()['id']

            title = filename.split('.')[0]
            # Test create a new leaderboard
            new_leaderboard = {
                "title": title,
                "story_extract": "",
                "is_public": True,
                "scene_id": scene_id,
                "story_id": story_id,
                "original_image_id": original_image_id,
            }

            response = client.post(
                "/sqlapp/leaderboards/", 
                json=new_leaderboard.copy(),
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {self.access_token}"}
            )
            print(f"leaderboard created: {response.json()}")
            assert response.status_code == 200

            leaderboard_dict[title] = response.json()['id']
        
        # Test read all leaderboards
        response = client.get("/sqlapp/leaderboards/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200

        # Read csv file
        with open('initial/entries/202408_Results.csv','r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                leaderboard_id = leaderboard_dict[row['Picture']]
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
                
                assert response.status_code == 200
                round_id = response.json()['id']

                new_generation = {
                    "round_id": round_id,
                    "created_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
                    "generated_time": 1,
                    "sentence": row['User sentence'],
                }

                response = client.put(
                    f"/sqlapp/round/{round_id}",
                    json=new_generation.copy(),
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {self.access_token}"},
                )
                
                assert response.status_code == 200
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
                assert response.status_code == 200
                
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
                assert response.status_code == 200

                # Test complete round
                response = client.post(
                    f"/sqlapp/round/{round_id}/end",
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {self.access_token}"},
                )
                assert response.status_code == 200

@pytest.mark.usefixtures("login")
class TestPlay2:
    username = os.getenv("USER_USERNAME")
    password = os.getenv("USER_PASSWORD")
    _client = client

    def test_play_2(self):
        # Get leaderboards
        response = client.get(
            "/sqlapp/leaderboards/",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        if not response.json():
            assert False
        leaderboard = response.json()[0]
        leaderboard_id = leaderboard['id']

        # Read csv file
        with open('initial/entries/202408_Results.csv','r') as f:
            reader = csv.DictReader(f)
            for row in reader:
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
                
                assert response.status_code == 200
                round_id = response.json()['id']

                new_generation = {
                    "round_id": round_id,
                    "created_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
                    "generated_time": 1,
                    "sentence": row['User sentence'],
                }

                response = client.put(
                    f"/sqlapp/round/{round_id}",
                    json=new_generation.copy(),
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {self.access_token}"},
                )
                
                assert response.status_code == 200
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
                assert response.status_code == 200
                
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
                assert response.status_code == 200

                # Test complete round
                response = client.post(
                    f"/sqlapp/round/{round_id}/end",
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {self.access_token}"},
                )
                assert response.status_code == 200
