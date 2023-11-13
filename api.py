import requests
import os
from dotenv import load_dotenv
from data_keys import (
    ScoringKeys as SK,
)

load_dotenv()
domain = os.environ["domain"]


def getMapData(mapName, apiKey):
    print(domain)
    try:
        resp = requests.get(
            f"{domain}/api/Game/getMapData?mapName={mapName}",
            headers={"x-api-key": apiKey},
        )
        resp.raise_for_status()
    except:
        print(resp)
        return None
    else:
        return resp.json()


def getGeneralData():
    try:
        resp = requests.get(f"{domain}/api/Game/getGeneralGameData")
        resp.raise_for_status()
    except:
        print(resp)
        return None
    else:
        return resp.json()


def getGame(id_):
    try:
        resp = requests.get(f"{domain}/api/Game/getGameData?gameId={id_}")
        resp.raise_for_status()
    except:
        print(resp)
        return None
    else:
        return resp.json()


def submit(
    mapName: str,
    solution,
    apiKey,
):
    try:
        resp = requests.post(
            f"{domain}/api/Game/submitSolution?mapName={mapName}",
            headers={"x-api-key": apiKey},
            json=solution,
        )
        resp.raise_for_status()
    except:
        print(resp)
        return None
    else:
        return resp.json()
