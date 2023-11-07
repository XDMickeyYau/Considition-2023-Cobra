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

def naive_ver1(mapEntity,  generalData):
    solution = {LK.locations: {}}

    for key in mapEntity[LK.locations]:
        location = mapEntity[LK.locations][key]
        name = location[LK.locationName]

        salesVolume = location[LK.salesVolume]
        locationType = location[LK.locationType]
        footfall = location[LK.footfall]

        min_sale = min(salesVolume,generalData[GK.f3100Data][GK.refillCapacityPerWeek])
        revenue = min_sale * generalData[GK.refillUnitData][GK.profitPerUnit]
        earnings = revenue - generalData[GK.f3100Data][GK.leasingCostPerWeek]
        
        if locationType in ['Grocery-store-large']:
            solution[LK.locations][name] = {
                LK.f9100Count: 1,
                LK.f3100Count: 0,
            }
        else: 
            solution[LK.locations][name] = {
                LK.f9100Count: 0,
                LK.f3100Count: 1,
            }
    return solution
        
def naive_ver2(mapEntity,  generalData):
    solution = {LK.locations: {}}

    for key in mapEntity[LK.locations]:
        location = mapEntity[LK.locations][key]
        name = location[LK.locationName]

        salesVolume = location[LK.salesVolume]
        locationType = location[LK.locationType]
        footfall = location[LK.footfall]

        min_sale = min(salesVolume,generalData[GK.f3100Data][GK.refillCapacityPerWeek])
        revenue = min_sale * generalData[GK.refillUnitData][GK.profitPerUnit]
        earnings = revenue - generalData[GK.f3100Data][GK.leasingCostPerWeek]
        
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
        elif earnings>0 or footfall>0: #: # salesVolume > generalData[GK.f3100Data][GK.refillCapacityPerWeek]:
            solution[LK.locations][name] = {
                LK.f9100Count: 0,
                LK.f3100Count: 1,
            }
    return solution
        
    
def algo(name, mapEntity,  generalData):
    return eval(name)(mapEntity,  generalData)