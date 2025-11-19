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
        "/sqlapp2/users/", 
        json=user_acc.copy(), 
        headers={"Content-Type": "application/json"}
    )

    response = client.post(
        "/sqlapp2/users/",
        json=user_acc2.copy(),
        headers={"Content-Type": "application/json"}
    )

@pytest.mark.usefixtures("login")
class TestAdmin:
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    _client = client

    def test_read_scenes(self):
        
        # Test read all scenes
        response = client.get(
            "/sqlapp2/scenes/",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        assert response.status_code == 200, response.json()

        # Test create a new scene
        new_scene = {
            "name": "Beatrix Potter",
            "prompt": "in the style of Beatrix Potter"
        }

        response = client.post("/sqlapp2/scene/", json=new_scene.copy(),headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"})
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
            response = client.post("/sqlapp2/scene/", json=scene.copy(),headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"})
            assert response.status_code == 201, response.json()

    def test_add_programs(self):
        programs = [
            {
                "name": "inlab_test",
                "description": "For in-lab experiment. Link disclosed to LMS",
                "feedback": "AWE+IMG"
            },
            {
                "name": "haga_sensei_test",
                "description": "For Haga sensei trial version",
                "feedback": "AWE+IMG"
            },
            {
                "name": "student_january_experiment",
                "description": "For January experiment in Saikyo High School year 1",
                "feedback": "AWE+IMG"
            },
            {
                "name": "student_1_sem_awe",
                "description": "for first semester experiment with automated writing evaluation",
                "feedback": "AWE"
            },
            {
                "name": "student_1_sem_img",
                "description": "for first semester experiment with generated images",
                "feedback": "IMG"
            }
        ]

        for program in programs:
            response = client.post("/sqlapp2/program", json=program.copy(),headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"})
            assert response.status_code == 201, response.json()

    def test_read_stories(self):

        # Test read all stories
        response = client.get("/sqlapp2/stories/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200, response.json()
        num_stories = len(response.json())

        # Test create a new story
        test_file_path = "tests/mice_story_for_test.txt"
        with open(test_file_path, "rb") as f:
            response = client.post(
                "/sqlapp2/story/",
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
        response = client.get("/sqlapp2/stories/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200, response.json()
        assert len(response.json()) == num_stories + 1

    