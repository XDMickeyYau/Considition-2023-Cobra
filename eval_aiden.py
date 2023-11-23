import os
import json
import time

from sklearn.model_selection import ParameterGrid
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

mapNames = [MN.stockholm]#[MN.goteborg, MN.uppsala, MN.vasteras, MN.linkoping][::-1]
results = []
game_folder = "my_games"
func_name = 'graph_mixed_score' #'graph_beam_score'
args_grid = {
    "mapNames": mapNames,
    "maxK":[25], 
    "maxL":[4], 
    "reverse_task":[False],
    "maxB":[15], 
}
args_grid = ParameterGrid(args_grid)

for args  in args_grid:
    ##Get map data from Considition endpoint
    print("args:",args)
    mapName = args.pop("mapNames")
    comment = str(args)
    mapEntity = getMapData(mapName, apiKey)
    ##Get non map specific data from Considition endpoint
    generalData = getGeneralData()

    if mapEntity and generalData:
        # ------------------------------------------------------------
        # ----------------Player Algorithm goes here------------------
        print(f"Playing map {mapName}")
        start = time.time()
        solution = algo(func_name,mapEntity, generalData, mapName, **args)
        duration = time.time()-start
        print(f"Duration: {duration}")
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
        result.insert(0, 'duration', duration)
        result.insert(0, 'mapName', mapName)
        result.insert(1, 'func_name', func_name)
        result.insert(1, 'timestamp', pd.Timestamp.now())
        result.insert(1, 'comment', comment)
        if not os.path.exists('results.csv'):
            result.to_csv('results.csv', index=False, mode='x',header=True)
        else:
            result.to_csv('results.csv', index=False, mode='a',header=False)
