import os
import sys, asyncio
import datetime, time, httpx
import pytest
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient

from main import app 
import random

pytest_plugins = ('pytest_asyncio',)

client = TestClient(app)

@pytest.mark.usefixtures("login_guest")
class TestPlay:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self._client = TestClient(app)
        self.access_token = self.get_access_token()

    def get_access_token(self):
        """Fetch access token for the user."""
        response = self._client.post(
            "/sqlapp/token", data={"username": self.username, "password": self.password}
        )
        assert response.status_code == 200, f"Failed to login user {self.username}."
        return response.json().get("access_token")

    async def test_submit_answer(self):
        print(f"User {self.username} with token started operation.")
        
        # Select a random leaderboard
        response = client.get("/sqlapp/leaderboards/", headers={"Authorization": f"Bearer {self.get_access_token()}"})

        leaderboards = response.json()
        leaderboard_id = random.choice(leaderboards)[0]["id"]

        # Create a new round
        new_round = {
            "leaderboard_id": leaderboard_id,
            "model": "gpt-4o-mini",
            "created_at": datetime.datetime.now().isoformat(),
        }

        response = client.post(
            "/sqlapp/round/", json=new_round, headers={"Authorization": f"Bearer {self.get_access_token()}"}
        )
        assert response.status_code == 201, f"Failed to create a new round for user {self.username}. {response.json()}"
        round_id = response.json()["id"]

        # Ask hint
        new_message = {
            "content": "I need a hint.",
            "created_at": datetime.datetime.now().isoformat(),
        }

        response = client.put(
            f"/sqlapp/round/{round_id}/chat", 
            json=new_message, 
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.get_access_token()}"}
        )
        assert response.status_code == 200, f"Failed to ask for a hint for user {self.username}."

        answer_results= []
        for i in range(5):
            
            random_answers = [
                "This is a picture of a rabbit wearing bikini.",
                "There is a man rided a horse, expressing his love to nature.",
                "The woman is holding a baby in her arms. The baby is crying.",
                "The consequence of the war is the destruction of the city.",
            ]

            # Submit answer
            new_generation = {
                "round_id": round_id,
                "created_at": datetime.datetime.now().isoformat(),
                "generated_time": i+1,
                "sentence": random.choice(random_answers),
            }

            response = client.put(
                f"/sqlapp/round/{round_id}/", 
                json=new_generation, 
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.get_access_token()}"}
            )

            assert response.status_code == 200, f"Failed to submit answer for user {self.username}."
            generation_id = response.json()["id"]
            correct_sentence = response.json()["correct_sentence"]

            # Generate interpretation
            interpretation_generation = {
                "id": generation_id,
                "correct_sentence": correct_sentence
            }

            response = client.put(
                f"/sqlapp/round/{round_id}/interpretation",
                    json=interpretation_generation.copy(),
                    headers={"Content-Type": "application/json",
                            "Authorization": f"Bearer {self.get_access_token()}"},
            )
            assert response.status_code == 200, f"Failed to get interpreted image for user {self.username}." 

            retry_delay = 10
            await asyncio.sleep(retry_delay)
            
            interpreted_counter = 0
            max_retries = 40
            # Get interpreted image
            while True:
                response = client.get(
                    f"/sqlapp/interpreted_image/{generation_id}",
                    headers={"Authorization": f"Bearer {self.get_access_token()}"},
                )

                if response.status_code == 200:
                    break
                interpreted_counter += 1
                if interpreted_counter >= max_retries:
                    return f"User {self.username} failed to obtain the interpreted image after {interpreted_counter} retries."
                await asyncio.sleep(retry_delay)

            # Complete the generation
            generation_com = {
                "id": generation_id,
                "at": datetime.datetime.now().isoformat(),
            }
            complete_counter = 0
            while True:
                response = client.put(
                    f"/sqlapp/round/{round_id}/complete",
                    json=generation_com.copy(),
                    headers={"Content-Type": "application/json",
                            "Authorization": f"Bearer {self.get_access_token()}"},
                )
                if response.status_code == 200:
                    break
                complete_counter += 1
                if complete_counter >= max_retries:
                    return f"User {self.username} failed to complete the generation after {complete_counter} retries."
                await asyncio.sleep(retry_delay)

            # Get the result
            result_counter = 0
            while True:
                response = client.get(
                    f"/sqlapp/generation/{generation_id}/score",
                    headers={"Authorization": f"Bearer {self.get_access_token()}"},
                )
                result = response.json()
                if response.status_code == 200 and isinstance(result, dict) and 'image_similarity' in result:
                    break
                result_counter += 1
                if result_counter >= max_retries:
                    return f"User {self.username} failed to get the result after {result_counter} retries."
                await asyncio.sleep(retry_delay)
            answer_results.append(f"User {self.username} operation result\nGet interpreted image: {interpreted_counter} retries\nComplete generation: {complete_counter} retries\nGet result: {result_counter} retries")
        return f"User {self.username} operation completed successfully.\n{answer_results}"


class TestPlays:
    def __init__(self, guest_ids):
        self.guest_ids = guest_ids
        self.guests = [
            TestPlay(f"guest{guest_id}", "hogehoge") for guest_id in guest_ids
        ]

@pytest.fixture
def play(request):
    return TestPlays(request.param)

# Pytest test case
@pytest.mark.parametrize("play", [range(1, 41)], indirect=True)
@pytest.mark.asyncio
async def test_users_with_login(play):
    """Test multi-user simulation with login."""
    async_tasks = []
    for guest in play.guests:
        
        async_tasks.append(
            guest.test_submit_answer()
        )
    awaited_results = await asyncio.gather(*async_tasks)


    # Assert the number of results matches the number of users
    assert len(awaited_results) == 40, "The number of results should match the number of users."

    # Optional: Check result format
    for i, result in enumerate(awaited_results, 1):
        print(result)
        assert f"User guest{i} operation completed successfully." in result, f"Unexpected result for user guest{i}: {result}"
