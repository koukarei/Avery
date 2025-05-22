import pytest
from fastapi.testclient import TestClient
import sys, os, asyncio,json
from httpx import AsyncClient, ReadTimeout
from httpx_ws import aconnect_ws
sys.path.append(os.getcwd())
from main import app 
from wsproto.utilities import LocalProtocolError

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

@pytest.mark.asyncio(loop_scope="session", scope="class")
@pytest.mark.usefixtures("login")
class TestPlay:

    @classmethod
    async def create(cls, username: str, password: str):
        instance = cls()
        instance.username = username
        instance.password = password
        instance._client = AsyncClient(base_url="http://localhost:8000", timeout=20)
        await instance.set_access_token()

        # Get leaderboard id
        assert instance.username is not None, "Username is not set."
        assert instance.password is not None, "Password is not set."
        
        response = await instance._client.get("/sqlapp2/leaderboards/", headers={"Authorization": f"Bearer {instance.access_token}"})
        assert response.status_code == 200, response.json()
        assert len(response.json()) > 0, "No leaderboard found."
        assert 'id' in response.json()[0][0], "No leaderboard id found."
        
        leaderboard = response.json()[0]
        instance.leaderboard_id = leaderboard[0]['id']

        instance.url = f"ws/{instance.leaderboard_id}?token={await instance.get_access_token()}"
        
        instance._ws_context = aconnect_ws(instance.url, instance._client, keepalive_ping_timeout_seconds=60)
        instance.ws = await instance._ws_context.__aenter__()
        return instance

    async def send_json(self, data, max_retries=3, backoff=1):
        """Send JSON data to the WebSocket."""
        last_exception = None
        for attempt in range(max_retries):
            try:
                text_data = json.dumps(data)
                return await self.ws.send_text(text_data)
                
            except ReadTimeout as e:
                last_exception = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2
            except LocalProtocolError:
                self.ws.close()
                self._ws_context = aconnect_ws(self.url, self._client, keepalive_ping_timeout_seconds=60)
                self.ws = await self._ws_context.__aenter__()

                await self.ws.send_text(json.dumps(self.resume_round))
                await self.ws.receive_text()
                # resend data
                await self.ws.send_text(text_data)

        raise last_exception

    async def receive_json(self, max_retries=3, backoff=1):
        """Receive JSON data from the WebSocket."""
        last_exception = None
        for attempt in range(max_retries):
            try:
                data = await self.ws.receive_text()
                data = json.loads(data)
                return data
            except ReadTimeout as e:
                last_exception = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2

        raise last_exception

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
        """Test WebSocket connection and interaction."""

        self.resume_round = {
                "action": "resume",
                "program": "inlab_test",
                "obj": {
                    "leaderboard_id": self.leaderboard_id,
                    "program": "inlab_test",
                    "model": "gpt-4o-mini",
                    "created_at": "2025-04-06T00:00:00Z",
                }
            }

            # Sent json data to the WebSocket to start the game
        await self.send_json(
            {
                "action": "start",
                "program": "inlab_test",
                "obj": {
                    "leaderboard_id": self.leaderboard_id,
                    "program": "inlab_test",
                    "model": "gpt-4o-mini",
                    "created_at": "2025-04-06T00:00:00Z",
                }
            }
        )

        # Receive json data from the WebSocket
        data = await self.receive_json()
            
        assert 'leaderboard' in data
        assert 'round' in data
        assert 'chat' in data

        leaderboard_image = data['leaderboard']['image']
        round = data['round']
        chat = data['chat']

        # Ask for a hint
        await self.send_json(
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

        data = await self.receive_json()
        assert 'chat' in data

        print(data['chat']['messages'])

        # Submit answer
        await self.send_json(
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
        data = await self.receive_json()

        assert 'leaderboard' in data
        assert 'round' in data
        assert 'chat' in data
        assert 'generation' in data

        print(data['chat']['messages'])
        generation = data['generation']
        print(generation['correct_sentence'])

        # Get evaluation result
        await self.send_json(
            {
                "action": "evaluate",
            }
        )

        data = await self.receive_json()

        while True:
            if 'feedback' in data:
                data = await self.receive_json()
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
        await self.send_json(
            {
                "action": "end",
            }
        )

        data = await self.receive_json()
        assert 'leaderboard' in data
        assert 'round' in data
        assert 'chat' in data

# Pytest test case
async def test_users_with_login():
    """Test multi-user simulation with login."""
    async_tasks = []
    for i in range(1, TEST_NUMBER):
        t = TestPlay()
        await t.create(
            username=f"test_acc{i}",
            password="hogehoge"
        )
        async_tasks.append(t.test_websocket())
    
    awaited_results = await asyncio.gather(*async_tasks)


    # Assert the number of results matches the number of users
    all_tests_num = len(awaited_results)
    assert all_tests_num == TEST_NUMBER-1, "The number of results should match the number of users."

    # Optional: Check result format
    for i, result in enumerate(awaited_results):
        print(result)
