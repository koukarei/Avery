import pytest
from fastapi.testclient import TestClient
import sys, os
sys.path.append(os.getcwd())
from main import app 

client = TestClient(app)

@pytest.mark.usefixtures("login")
class TestPlay:
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    _client = client
        
    async def test_websocket(self):
        # Get leaderboard id
        response = self._client.get("/avery/sqlapp2/leaderboards/admin/", headers={"Authorization": f"Bearer {self.access_token}"})
        assert response.status_code == 200, response.json()
        assert len(response.json()) > 0, "No leaderboard found."
        assert 'id' in response.json()[0], "No leaderboard id found."
        
        leaderboard = response.json()[0]
        leaderboard_id = leaderboard['id']


        with self._client.websocket_connect(
            f"/avery/sqlapp2/ws/{leaderboard_id}?token={self.access_token}",
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
            assert 'generation' in data

            
