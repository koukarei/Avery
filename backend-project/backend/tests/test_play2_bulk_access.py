import pytest
from fastapi.testclient import TestClient
import sys, os, asyncio
sys.path.append(os.getcwd())
from main import app 

client = TestClient(app)

TEST_NUMBER = 11

def test_create_test_accounts():
    """Create test accounts for multi-user simulation."""
    for i in range(1, TEST_NUMBER):
        user_acc = {
            "username": f"test_acc{i}",
            "email": f"test_acc{i}@example.com",
            "password": "hogehoge",
            "display_name": f"Test Account {i}"
        }
        response = client.post(
            "/sqlapp2/users/", 
            json=user_acc.copy(), 
            headers={"Content-Type": "application/json"}
        )

@pytest.mark.usefixtures("login")
class Test_TestAC:
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    _client = client
        
    async def test_deactivate_test_accounts(self):
        """Deactivate test accounts after multi-user simulation."""
        for i in range(1, TEST_NUMBER):
            user_id = 1
            response = self._client.put(
                f"/sqlapp2/users/{user_id}", 
                json={
                    "username": f"test_acc{i}",
                    "is_active": False,
                }, 
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"}
            )
            assert response.status_code == 200, response.json()

    async def test_activate_test_accounts(self):
        """Activate test accounts after multi-user simulation."""
        for i in range(1, TEST_NUMBER):
            user_id = 1
            response = self._client.put(
                f"/sqlapp2/users/{user_id}", 
                json={
                    "username": f"test_acc{i}",
                    "is_active": True,
                }, 
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"}
            )
            assert response.status_code == 200, response.json()

@pytest.mark.usefixtures("login")
class TestPlay:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self._client = TestClient(app)
        self.access_token = self.get_access_token()

    def get_access_token(self):
        """Fetch access token for the user."""
        response = self._client.post(
            "/sqlapp2/token", data={"username": self.username, "password": self.password}
        )
        assert response.status_code == 200, f"Failed to login user {self.username}."
        return response.json().get("access_token")
        
    async def test_websocket(self):
        # Get leaderboard id
        response = self._client.get("/sqlapp2/leaderboards/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200, response.json()
        assert len(response.json()) > 0, "No leaderboard found."
        assert 'id' in response.json()[0][0], "No leaderboard id found."
        
        leaderboard = response.json()[0]
        leaderboard_id = leaderboard[0]['id']

        with self._client.websocket_connect(
            f"/sqlapp2/ws/{leaderboard_id}?token={self.access_token}",
        ) as websocket:
            # Sent json data to the WebSocket to start the game
            websocket.send_json(
                {
                    "action": "start",
                    "program": "inlab_test",
                    "obj": {
                        "leaderboard_id": leaderboard_id,
                        "program": "inlab_test",
                        "model": "gpt-4o-mini",
                        "created_at": "2025-04-06T00:00:00Z",
                    }
                }
            )

            # Receive json data from the WebSocket
            data = websocket.receive_json()
                
            assert 'leaderboard' in data
            assert 'round' in data
            assert 'chat' in data

            leaderboard_image = data['leaderboard']['image']
            round = data['round']
            chat = data['chat']

            # Ask for a hint
            websocket.send_json(
                {
                    "action": "hint",
                    "program": "inlab_test",
                    "obj": {
                        "is_hint": True,
                        "content": "ヒントをちょうだい",
                        "created_at": "2025-04-06T00:00:00Z",
                    }
                }
            )

            data = websocket.receive_json()
            assert 'chat' in data

            print(data['chat']['messages'])

            # Submit answer
            websocket.send_json(
                {
                    "action": "submit",
                    "program": "inlab_test",
                    "obj": {
                        "round_id": round['id'],
                        "created_at": "2025-04-06T00:00:00Z",
                        "generated_time": round['generated_time'],
                        "sentence": "An old man crafted a wooden duck maciliously."
                    }
                }
            )
            data = websocket.receive_json()

            assert 'leaderboard' in data
            assert 'round' in data
            assert 'chat' in data
            assert 'generation' in data

            print(data['chat']['messages'])
            generation = data['generation']
            print(generation['correct_sentence'])

            # Get evaluation result
            websocket.send_json(
                {
                    "action": "evaluate",
                }
            )

            data = websocket.receive_json()

            while True:
                if 'feedback' in data:
                    data = websocket.receive_json()
                else:
                    break
            
            assert 'leaderboard' in data
            assert 'round' in data
            assert 'chat' in data
            assert 'generation' in data

            print(data['chat']['messages'])
            generation = data['generation']

            assert 'interpreted_image' in generation
            assert 'image_similarity' in generation

            # end the game
            websocket.send_json(
                {
                    "action": "end",
                }
            )

            data = websocket.receive_json()
            assert 'leaderboard' in data
            assert 'round' in data
            assert 'chat' in data

        
class TestPlays:
    def __init__(self, test_ids):
        self.test_ids = test_ids
        self.tests = [
            TestPlay(f"test_acc{test_id}", "hogehoge") for test_id in test_ids
        ]

@pytest.fixture
def play(request):
    return TestPlays(request.param)

# Pytest test case
@pytest.mark.parametrize("play", [range(1, TEST_NUMBER)], indirect=True)
@pytest.mark.asyncio
async def test_users_with_login(play):
    """Test multi-user simulation with login."""
    async_tasks = []
    for t in play.tests:
        
        async_tasks.append(
            t.test_websocket()
        )
    awaited_results = await asyncio.gather(*async_tasks)


    # Assert the number of results matches the number of users
    all_tests_num = len(awaited_results)
    assert all_tests_num == TEST_NUMBER-1, "The number of results should match the number of users."

    # Optional: Check result format
    for i, result in enumerate(awaited_results):
        print(result)
        assert f"Test User {i} operation completed successfully." in result, f"Unexpected result for user test_acc{i}: {result}"