import os
import json
from scoring import calculateScore, distanceBetweenPoint
from api import getGeneralData, getMapData, submit
from data_keys import (
    MapNames as MN,
    LocationKeys as LK,
    ScoringKeys as SK,
    GeneralKeys as GK,
    CoordinateKeys as CK,
)
from dotenv import load_dotenv
import networkx as nx

# def naive_ver1(mapEntity,  generalData):
#     solution = {LK.locations: {}}

#     for key in mapEntity[LK.locations]:
#         location = mapEntity[LK.locations][key]
#         name = location[LK.locationName]

#         salesVolume = location[LK.salesVolume]
#         locationType = location[LK.locationType]
#         footfall = location[LK.footfall]

#         min_sale = min(salesVolume,generalData[GK.f3100Data][GK.refillCapacityPerWeek])
#         revenue = min_sale * generalData[GK.refillUnitData][GK.profitPerUnit]
#         earnings = revenue - generalData[GK.f3100Data][GK.leasingCostPerWeek]
        
#         if locationType in ['Grocery-store-large']:
#             solution[LK.locations][name] = {
#                 LK.f9100Count: 1,
#                 LK.f3100Count: 0,
#             }
#         else: 
#             solution[LK.locations][name] = {
#                 LK.f9100Count: 0,
#                 LK.f3100Count: 1,
#             }
#     return solution

def create_graph(mapEntity, generalData):
    G = nx.Graph()
    # add nodes
    for key in mapEntity[LK.locations]:
        location = mapEntity[LK.locations][key] 
        location["available"] = True
        G.add_node(key, **location)
    # add edges if distance is less than willingness to travel
    for key_from in mapEntity[LK.locations]:
        for key_to in mapEntity[LK.locations]:
                if key_from == key_to:
                    continue
                distance = distanceBetweenPoint(
                    mapEntity[LK.locations][key_from][CK.latitude],
                    mapEntity[LK.locations][key_from][CK.longitude],
                    mapEntity[LK.locations][key_to][CK.latitude],
                    mapEntity[LK.locations][key_to][CK.longitude],
                )
                if distance < generalData[GK.willingnessToTravelInMeters]:
                    G.add_edge(key_from, key_to)
    return G


def deploy_refill(sales, generalData):

    sales_F3 = min(sales,generalData[GK.f3100Data][GK.refillCapacityPerWeek])
    sales_F9 = min(sales,generalData[GK.f9100Data][GK.refillCapacityPerWeek])

    revenue_F3 = sales_F3  * generalData[GK.refillUnitData][GK.profitPerUnit]
    revenue_F9 = sales_F9  * generalData[GK.refillUnitData][GK.profitPerUnit]

    earnings_F3 = revenue_F3 - generalData[GK.f3100Data][GK.leasingCostPerWeek]
    earnings_F9 = revenue_F9 - generalData[GK.f9100Data][GK.leasingCostPerWeek]

    co2Savings_F3 = (
        sales_F3
        * (
            generalData[GK.classicUnitData][GK.co2PerUnitInGrams]
            - generalData[GK.refillUnitData][GK.co2PerUnitInGrams]
        )
        - generalData[GK.f3100Data][GK.staticCo2]
    )
    co2Savings_F9 = (
        sales_F9
        * (
            generalData[GK.classicUnitData][GK.co2PerUnitInGrams]
            - generalData[GK.refillUnitData][GK.co2PerUnitInGrams]
        )
        -  generalData[GK.f9100Data][GK.staticCo2]
    )

    total_F3 = (
            co2Savings_F3
            * generalData[GK.co2PricePerKiloInSek]
            + earnings_F3
        )
    total_F9 = (
            co2Savings_F9
            * generalData[GK.co2PricePerKiloInSek]
            + earnings_F9
        )
    if total_F9 > total_F3:
        return {
                LK.f9100Count: 1,
                LK.f3100Count: 0,
            }, total_F9
    elif total_F3 > 0:
        return {
                LK.f9100Count: 0,
                LK.f3100Count: 1,
            }, total_F3
    else:
        return None, 0

def aggregate_sales(key, S, generalData):
    sales = S.nodes[key][LK.salesVolume]
    neighbors = nx.all_neighbors(S, key)
    for neighbor in neighbors:
        sales += S.nodes[neighbor][LK.salesVolume]*generalData[GK.refillDistributionRate]
    return sales


def graph_greedy(mapEntity, generalData):
    solution = {LK.locations: dict()}
    G = create_graph(mapEntity, generalData)
    for C in nx.connected_components(G):
        # print("*************")
        S = G.subgraph(C)
        for key in S.nodes():
            sales = aggregate_sales(key, S, generalData)
            S.nodes[key]['real_sales'] = sales
            deployment, score = deploy_refill(S.nodes[key]['real_sales'], generalData)           
            S.nodes[key]['solution'] = deployment
            S.nodes[key]['score'] = score
        sorted_node = sorted(S.nodes(), key=lambda n: (S.nodes[n]['real_sales'], S.nodes[n][LK.footfall]),reverse=True)
        disabled = set()
        for key in sorted_node:
            # print(key, disabled, S.nodes[key][LK.locationType], int(S.nodes[key]['score']), S.nodes[key][LK.footfall])
            if key not in disabled:
                name = S.nodes[key][LK.locationName]
                if S.nodes[key]['solution'] is not None:
                    solution[LK.locations][name] = S.nodes[key]['solution']
                disabled.add(key)
                disabled.update(nx.all_neighbors(S, key))
                # print("added")
    return solution

     
    
def algo(name, mapEntity,  generalData):
    func_map = {
        "graph_greedy": graph_greedy,
    }
    func = func_map[name]
    return func(mapEntity,  generalData)