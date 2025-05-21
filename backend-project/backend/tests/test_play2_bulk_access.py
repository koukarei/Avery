import pytest
from fastapi.testclient import TestClient
import sys, os, asyncio,json
from httpx import AsyncClient
from httpx_ws import aconnect_ws
sys.path.append(os.getcwd())
from main import app 

TEST_NUMBER = 6

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
    _client = TestClient(app)
        
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

def send_json(websocket, data):
    """Send JSON data to the WebSocket."""
    data = json.dumps(data)
    websocket.send_text(data)

def receive_json(websocket):
    data = websocket.receive_text()
    data = json.loads(data)
    return data

@pytest.mark.asyncio(scope="class")
@pytest.mark.usefixtures("login")
class TestPlay:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self._client = AsyncClient(base_url="http://localhost:8000")
        self.access_token = None

    async def get_access_token(self):
        """Fetch access token for the user."""
        response = await self._client.post(
            "/sqlapp2/token", data={"username": self.username, "password": self.password}
        )
        assert response.status_code == 200, f"Failed to login user {self.username}."
        return response.json().get("access_token")
    
    async def set_access_token(self):
        self.access_token = await self.get_access_token()
        
    async def test_websocket(self):
        await self.set_access_token()
        # Get leaderboard id
        response = await self._client.get("/sqlapp2/leaderboards/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200, response.json()
        assert len(response.json()) > 0, "No leaderboard found."
        assert 'id' in response.json()[0][0], "No leaderboard id found."
        
        leaderboard = response.json()[0]
        leaderboard_id = leaderboard[0]['id']

        async with aconnect_ws(
            f"/sqlapp2/ws/{leaderboard_id}?token={self.access_token}",
            self._client
        ) as websocket:
            # Sent json data to the WebSocket to start the game
            send_json(websocket,
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
            data = receive_json(websocket)
                
            assert 'leaderboard' in data
            assert 'round' in data
            assert 'chat' in data

            leaderboard_image = data['leaderboard']['image']
            round = data['round']
            chat = data['chat']

            # Ask for a hint
            send_json(websocket,
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

            data = receive_json(websocket)
            assert 'chat' in data

            print(data['chat']['messages'])

            # Submit answer
            send_json(websocket,
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
            data = receive_json(websocket)

            assert 'leaderboard' in data
            assert 'round' in data
            assert 'chat' in data
            assert 'generation' in data

            print(data['chat']['messages'])
            generation = data['generation']
            print(generation['correct_sentence'])

            # Get evaluation result
            send_json(websocket,
                {
                    "action": "evaluate",
                }
            )

            data = receive_json(websocket)

            while True:
                if 'feedback' in data:
                    data = receive_json(websocket)
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
            send_json(websocket,
                {
                    "action": "end",
                }
            )

            data = receive_json(websocket)
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
async def test_users_with_login(play):
    """Test multi-user simulation with login."""
    async_tasks = [
            t.test_websocket()
            for t in play.tests
    ]
    
    awaited_results = await asyncio.gather(*async_tasks)


    # Assert the number of results matches the number of users
    all_tests_num = len(awaited_results)
    assert all_tests_num == TEST_NUMBER-1, "The number of results should match the number of users."

    # Optional: Check result format
    for i, result in enumerate(awaited_results):
        print(result)