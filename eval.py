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
import optimal_machine_count

load_dotenv()
apiKey = os.environ["apiKey"]

mapNames = [MN.goteborg, MN.uppsala, MN.vasteras, MN.linkoping]
results = []
func_name = 'naive_ver2'

for mapName in mapNames:
    ##Get map data from Considition endpoint
    mapEntity = getMapData(mapName, apiKey)
    ##Get non map specific data from Considition endpoint
    generalData = getGeneralData()

    if mapEntity and generalData:
        # ------------------------------------------------------------
        # ----------------Player Algorithm goes here------------------
        solution = algo(func_name,mapEntity, generalData)
        linp_res = optimal_machine_count.optimal_f3f9_count(solution, mapEntity, generalData)
        for i in range(len(linp_res[0])):
            solution[LK.locations][linp_res[0][i]] = {LK.f3100Count: linp_res[1][i * 2],
                                                     LK.f9100Count: linp_res[1][i * 2 + 1]}
        # ----------------End of player code--------------------------
        # ------------------------------------------------------------

        # Score solution locally
        score = calculateScore(mapName, solution, mapEntity, generalData)

        result = pd.Series(score[SK.gameScore]).to_frame().T
        result.insert(0, 'mapName', mapName)
        results.append(result)


results = pd.concat(results,axis=0)
results.insert(0, 'func_name', func_name)
results.insert(0, 'timestamp', pd.Timestamp.now())
print(results)
if not os.path.exists('results.csv'):
    results.to_csv('results.csv', index=False, mode='x',header=True)
else:
    results.to_csv('results.csv', index=False, mode='a',header=False)
