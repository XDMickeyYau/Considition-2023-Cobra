import os
import json
from algorithms import algo
from scoring import calculateScore
from api import getGeneralData, getMapData, submit
from data_keys import (
    MapNames as MN,
    LocationKeys as LK,
    ScoringKeys as SK,
)
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
apiKey = os.environ["apiKey"]

mapNames = [MN.goteborg, MN.uppsala, MN.vasteras, MN.linkoping][::-1]
results = []
game_folder = "my_games"
func_name = 'graph_mixed_score' #'graph_beam_score'
args = {
    "maxK":30, 
    "maxL":4, 
    "maxB":12, 
    "reverse_task":False
}
comment = str(args)#"remove neighbor assumption"
for mapName in mapNames:
    ##Get map data from Considition endpoint
    mapEntity = getMapData(mapName, apiKey)
    ##Get non map specific data from Considition endpoint
    generalData = getGeneralData()

    if mapEntity and generalData:
        # ------------------------------------------------------------
        # ----------------Player Algorithm goes here------------------
        print(f"Playing map {mapName}")
        solution = algo(func_name,mapEntity, generalData, mapName, **args)
        # ----------------End of player code--------------------------
        # ------------------------------------------------------------

        # Score solution locally
        score = calculateScore(mapName, solution, mapEntity, generalData)
        print(f"Score: {score[SK.gameScore]}")
        id_ = score[SK.gameId]
        print(f"Storing game with id {id_}.")
        print(f"Enter {id_} into visualization.ipynb for local vizualization ")

        # Store solution locally for visualization
        with open(f"{game_folder}/{id_}.json", "w", encoding="utf8") as f:
            json.dump(score, f, indent=4)

        # Submit and and get score from Considition app
        print(f"Submitting solution to Considtion 2023 \n")

        scoredSolution = submit(mapName, solution, apiKey)
        if scoredSolution:
            print("Successfully submitted game")
            print(f"id: {scoredSolution[SK.gameId]}")
            print(f"Score: {scoredSolution[SK.gameScore]}")

        result = pd.Series(score[SK.gameScore]).to_frame().T
        result.insert(0, 'mapName', mapName)
        results.append(result)

results = pd.concat(results,axis=0)
results.insert(0, 'func_name', func_name)
results.insert(0, 'timestamp', pd.Timestamp.now())
results.insert(0, 'comment', comment)
print(results)
if not os.path.exists('results.csv'):
    results.to_csv('results.csv', index=False, mode='x',header=True)
else:
    results.to_csv('results.csv', index=False, mode='a',header=False)