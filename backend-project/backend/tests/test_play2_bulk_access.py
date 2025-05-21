import pytest
from fastapi.testclient import TestClient
import sys, os, asyncio,json
from httpx import AsyncClient, ReadTimeout
from httpx_ws import aconnect_ws
sys.path.append(os.getcwd())
from main import app 

TEST_NUMBER = 11

def test_create_test_accounts():
    client = TestClient(app)
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

async def send_json(websocket, data, max_retries=3, backoff=1):
    """Send JSON data to the WebSocket."""
    last_exception = None
    for attempt in range(max_retries):
        try:
            data = json.dumps(data)
            return await websocket.send_text(data)
            
        except ReadTimeout as e:
            last_exception = e
            if attempt < max_retries - 1:
                await asyncio.sleep(backoff)
                backoff *= 2
    raise last_exception

async def receive_json(websocket, max_retries=3, backoff=1):
    """Receive JSON data from the WebSocket."""
    last_exception = None
    for attempt in range(max_retries):
        try:
            data = await websocket.receive_text()
            data = json.loads(data)
            return data
        except ReadTimeout as e:
            last_exception = e
            if attempt < max_retries - 1:
                await asyncio.sleep(backoff)
                backoff *= 2
    raise last_exception

@pytest.mark.asyncio(loop_scope="session", scope="class")
@pytest.mark.usefixtures("login")
class TestPlay:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self._client = AsyncClient(base_url="http://localhost:8000", timeout=20)
        self.access_token = None

    async def get_access_token(self, max_retries=3, backoff=1):
        """Fetch access token for the user."""
        for attempt in range(max_retries):
            try:
                response = await self._client.post(
                    "/sqlapp2/token", data={"username": self.username, "password": self.password}
                )
                if response.status_code == 200:
                    return response.json().get("access_token")
            except ReadTimeout as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    raise e
    
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
            self._client,
            keepalive_ping_timeout_seconds=60
        ) as websocket:
            # Sent json data to the WebSocket to start the game
            await send_json(websocket,
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
            data = await receive_json(websocket)
                
            assert 'leaderboard' in data
            assert 'round' in data
            assert 'chat' in data

            leaderboard_image = data['leaderboard']['image']
            round = data['round']
            chat = data['chat']

            # Ask for a hint
            await send_json(websocket,
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

            data = await receive_json(websocket)
            assert 'chat' in data

            print(data['chat']['messages'])

            # Submit answer
            await send_json(websocket,
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
            data = await receive_json(websocket)

            assert 'leaderboard' in data
            assert 'round' in data
            assert 'chat' in data
            assert 'generation' in data

            print(data['chat']['messages'])
            generation = data['generation']
            print(generation['correct_sentence'])

            # Get evaluation result
            await send_json(websocket,
                {
                    "action": "evaluate",
                }
            )

            data = await receive_json(websocket)

            while True:
                if 'feedback' in data:
                    data = await receive_json(websocket)
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
            await send_json(websocket,
                {
                    "action": "end",
                }
            )

            data = await receive_json(websocket)
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