import os
import sys
sys.path.append(os.getcwd())
import csv

from fastapi.testclient import TestClient

from main import app 
from fastapi import UploadFile

client = TestClient(app)

def test_play():
    # Create leaderboards
    response = client.post("/leaderboards/create")

    # Read csv file
    with open('initial/entries/202408_Results.csv','r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pass