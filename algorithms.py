import copy
import itertools
import os
import json

from sklearn.model_selection import ParameterGrid
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
            }, {
                SK.earnings: earnings_F9,
                SK.co2Savings: co2Savings_F9,
                SK.total: total_F9,
            }
    elif total_F3 > 0:
        return {
                LK.f9100Count: 0,
                LK.f3100Count: 1,
            }, {
                SK.earnings: earnings_F3,
                SK.co2Savings: co2Savings_F3,
                SK.total: total_F3,
            }
    else:
        return None, {}

def aggregate_sales(key, S, generalData):
    sales = S.nodes[key][LK.salesVolume]
    neighbors = nx.all_neighbors(S, key)
    for neighbor in neighbors:
        sales += S.nodes[neighbor][LK.salesVolume]*generalData[GK.refillDistributionRate]
    sales = sales*generalData[GK.refillSalesFactor]
    return sales

def update_subgraph(S, generalData):
    for key in S.nodes():
        sales = aggregate_sales(key, S, generalData)
        S.nodes[key]['real_sales'] = sales
        deployment, score_dict = deploy_refill(S.nodes[key]['real_sales'], generalData)
        print(key, S.degree[key], S.nodes[key][LK.locationType], sales, deployment, score_dict)
        if deployment is not None:      
            S.nodes[key]['solution'] = deployment
            S.nodes[key][SK.earnings] = score_dict[SK.earnings] / 1000
            S.nodes[key][SK.co2Savings] = score_dict[SK.co2Savings] / 1000
            S.nodes[key]['score'] = score_dict[SK.total] / 1000
            S.nodes[key][LK.footfall] = S.nodes[key][LK.footfall] / 1000
    return S

def deploy_subgraph(S, sorted_node, solution, total_score):
    disabled = set()
    for key in sorted_node:
        if key not in disabled:
            name = S.nodes[key][LK.locationName]
            if 'solution' in S.nodes[key]:
                # print(key, S.nodes[key][SK.earnings], S.nodes[key][SK.co2Savings], S.nodes[key]['score'], S.nodes[key][LK.footfall])
                solution[LK.locations][name] = S.nodes[key]['solution']
                total_score[SK.earnings] += S.nodes[key][SK.earnings] 
                total_score[SK.co2Savings] += S.nodes[key][SK.co2Savings]
                total_score['base_score'] += S.nodes[key]['score'] 
                total_score['footfall'] += S.nodes[key][LK.footfall] 
            disabled.add(key)
            disabled.update(nx.all_neighbors(S, key))
            # print("added")
    return solution


def graph_greedy(mapEntity, generalData, mapName):
    solution = {LK.locations: dict()}
    G = create_graph(mapEntity, generalData)
    total_score = {
        SK.earnings: 0,
        SK.co2Savings: 0,
        "base_score": 0,
        "footfall": 0,
    }
    for C in nx.connected_components(G):
        S = G.subgraph(C)
        S = update_subgraph(S, generalData)
        sorted_node = sorted(S.nodes(), key=lambda n: (S.nodes[n]['real_sales'], S.nodes[n][LK.footfall]),reverse=True)
        solution = deploy_subgraph(S, sorted_node, solution, total_score)
    # print("total_score",total_score)
    # print("total_score",total_score['base_score']*(1+total_score['footfall']))
    return solution

def get_mapEntity_subgraph(mapEntity, C):
    mapEntity_subgraph = {k:v for k,v in mapEntity.items() if k != LK.locations}
    mapEntity_subgraph[LK.locations] = {key: mapEntity[LK.locations][key] for key in C}
    return mapEntity_subgraph


def cal_total_score(scoredSolution,generalData):
    return round(
        (
            scoredSolution[SK.co2Savings]
            * generalData[GK.co2PricePerKiloInSek]
            + scoredSolution[SK.earnings]
        )
        * (1 + scoredSolution[SK.totalFootfall]),
        2,
    )

def graph_greedy_score(mapEntity, generalData, mapName):
    solution = {LK.locations: dict()}
    G = create_graph(mapEntity, generalData)
    total_score = {
        SK.earnings: 0,
        SK.co2Savings: 0,
        SK.totalFootfall: 0,
    }    
    for C in sorted (nx.connected_components(G), key=lambda C: len(C)):
        mapEntity_subgraph = get_mapEntity_subgraph(mapEntity, C)
        solution_subgraph = {LK.locations:dict()}
        if len(C) == 1:
            key = list(C)[0]
            test = deploy_refill_simple(G.nodes[key][LK.locationType])
            if test is not None:
                solution_subgraph[LK.locations][key] = test
                scoredSolution = calculateScore(mapName, solution_subgraph, mapEntity_subgraph, generalData)
                for score_key in total_score:
                    total_score[score_key] += scoredSolution[SK.gameScore][score_key]
        else:
            S = G.subgraph(C)
            available = copy.deepcopy(C)
            best_total = 0
            while len(available):
                # place refill station at each step
                best_solution = None
                for key in available:
                    for solution_test in [{LK.f9100Count: 1, LK.f3100Count: 0}, {LK.f9100Count: 0, LK.f3100Count: 1}]:
                        solution_subgraph[LK.locations][key] = solution_test
                        scoredSolution = calculateScore(mapName, solution_subgraph, mapEntity_subgraph, generalData)
                        for score_key in total_score:
                            total_score[score_key] += scoredSolution[SK.gameScore][score_key]
                        total = cal_total_score(total_score,generalData)
                        if total > best_total:
                            best_solution = (key, solution_test)
                            best_total = total
                        for score_key in total_score:
                            total_score[score_key] -= scoredSolution[SK.gameScore][score_key]
                        solution_subgraph[LK.locations].pop(key) 
                
                if best_solution is not None:
                    key, best_solution = best_solution
                    solution_subgraph[LK.locations][key] = best_solution
                    available.remove(key)
                    available -= set(nx.all_neighbors(S, key))
                else: 
                    break
        
        print(solution)
        print(C,solution_subgraph)
        solution[LK.locations].update(solution_subgraph[LK.locations])
    return solution

def deploy_refill_simple(locationtype):
    # ['Grocery-store-large','Grocery-store','Gas-station','Convenience','Kiosk']
    if locationtype == 'Grocery-store-large':
        return {
                LK.f9100Count: 1,
                LK.f3100Count: 0,
        }
    elif locationtype != 'Kiosk':
        return {
                LK.f9100Count: 0,
                LK.f3100Count: 1,
        }
    else:
        return None

def brute_force(mapEntity, generalData, mapName):
    print("brute force")
    solution_grid = dict()
    G = create_graph(mapEntity, generalData)
    print("graph created")
    for node in G.nodes:
        if G.degree[node] == 0:
            solution_grid[node] = [deploy_refill_simple(G.nodes[node][LK.locationType])]
        else:
            solution_grid[node] = [
                None,
                {
                LK.f9100Count: 0,
                LK.f3100Count: 1,
                },
                {
                LK.f9100Count: 1,
                LK.f3100Count: 0,
                },    
            ]
        print(G.degree[node], G.nodes[node][LK.locationType], solution_grid[node])
    print("solution_grid",len(solution_grid))
    L = [[(k, v) for v in vs] for k, vs in solution_grid.items()]
    print("L",len(L))
    solutions = list(map(dict, itertools.product(*L)))
    print("POSSIBLE SOLUTION:", len(solutions))
    max_score = 0
    max_solution = None
    for solution in solutions:
        solution = {k:v for k,v in solution.items() if v is not None}
        solution = {LK.locations: solution}
        score = calculateScore(mapName, solution, mapEntity, generalData)
        if score > max_score:
            max_score = score
            max_solution = solution
    return max_solution

def algo(name, mapEntity,  generalData, mapName):
    func_map = {
        "graph_greedy": graph_greedy,
        "brute_force": brute_force,
        "graph_greedy_score":graph_greedy_score
    }
    func = func_map[name]
    return func(mapEntity,  generalData, mapName)