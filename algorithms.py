import os
import json
from scoring import calculateScore
from api import getGeneralData, getMapData, submit
from data_keys import (
    MapNames as MN,
    LocationKeys as LK,
    ScoringKeys as SK,
    GeneralKeys as GK,
)
from dotenv import load_dotenv

def naive(mapEntity,  generalData):
    solution = {LK.locations: {}}

    for key in mapEntity[LK.locations]:
        location = mapEntity[LK.locations][key]
        name = location[LK.locationName]

        salesVolume = location[LK.salesVolume]
        locationType = location[LK.locationType]
        footfall = location[LK.footfall]
        
        if locationType in ['Grocery-store-large']:
            solution[LK.locations][name] = {
                LK.f9100Count: 1,
                LK.f3100Count: 0,
            }
        elif locationType in ['Grocery-store']:
            solution[LK.locations][name] = {
                LK.f9100Count: 0,
                LK.f3100Count: 1,
            }
        else: # salesVolume > generalData[GK.f3100Data][GK.refillCapacityPerWeek]:
            solution[LK.locations][name] = {
                LK.f9100Count: 0,
                LK.f3100Count: 1,
            }
    return solution
        
    
