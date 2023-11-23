import copy
import itertools
from multiprocessing import Pool

from scoring import calculateScore, distanceBetweenPoint
from data_keys import (
    MapNames as MN,
    LocationKeys as LK,
    ScoringKeys as SK,
    GeneralKeys as GK,
    CoordinateKeys as CK,
)
import networkx as nx
import heapq

from functools import total_ordering

@total_ordering
class KeyDict(object):
    """a custom class for ordering solutions in minheap"""
    def __init__(self, key, dct):
        self.key = key
        self.dct = dct

    def __lt__(self, other):
        return self.key < other.key

    def __eq__(self, other):
        return self.key == other.key

    def __repr__(self):
        return '{0.__class__.__name__}(key={0.key}, dct={0.dct})'.format(self)

def create_graph(mapEntity, generalData):
    """Create networkx graph from mapEntity
    1. For each location in map, add it to the graph
    2. For each pair of locations, add edges if distance is less than willingness to travel
    Returns
    ------
    graph
        a networkx graph
    """
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

def get_mapEntity_subgraph(mapEntity, C):
    """Get a subset of mapEntity where all the locations are in subgraph C
    Returns
    ------
    mapEntity_subgraph
        a subset of mapEntity in subgraph C
    """
    mapEntity_subgraph = {k:v for k,v in mapEntity.items() if k != LK.locations}
    mapEntity_subgraph[LK.locations] = {key: mapEntity[LK.locations][key] for key in C}
    return mapEntity_subgraph

def get_solution_subgreaph(solution, C):
    """Get a subset of solution where all the locations are in subgraph C
    Returns
    ------
    solution_subgraph
        a subset of solution in subgraph C
    """
    solution_subgraph = {
        LK.locations:{
            k:solution[LK.locations][k] for k in C if k in solution[LK.locations]
            }
        }
    return solution_subgraph

def refine_footfall(scoredSolution):
    """Fix rounding error in footfall using scoredSolution calculated from the scoring function
    Returns
    ------
    footfall
        footfall fixed
    """
    footfall = 0
    for node in scoredSolution[LK.locations]:
        footfall += scoredSolution[LK.locations][node][LK.footfall]
    scoredSolution[SK.gameScore][SK.totalFootfall] = footfall / 1000
    return footfall

def update_total_score(total_score,scoredSolution,generalData,add=1):
    """Update the game score dictionary total_score using scoredSolution calculated from the scoring function
    Returns
    ------
    total_score
        total score updated
    
    """
    refine_footfall(scoredSolution)
    for score_key in total_score:
        total_score[score_key] += scoredSolution[SK.gameScore][score_key] * add
    total_score[SK.total] = (
        (
            total_score[SK.co2Savings]
            * generalData[GK.co2PricePerKiloInSek]
            + total_score[SK.earnings]
        )
        * (1 + total_score[SK.totalFootfall])
    )
    return total_score[SK.total]

def try_placing_refill(solution_subgraph, key, solution_test, total_score, mapEntity_subgraph, generalData, mapName):
    """Simulate the effect of placing a refill station in signle location in a subgraph
    1. Place the refill stations 
    2. Calculate the total score earned
    3. Remove the refill stations
    Returns
    ------
    total
        total score would be earned
    footfall
        total footfall would be gained
    """
    solution_subgraph[LK.locations][key] = solution_test
    scoredSolution = calculateScore(mapName, solution_subgraph, mapEntity_subgraph, generalData)
    footfall = refine_footfall(scoredSolution)
    # Check if score is better
    total = update_total_score(total_score,scoredSolution,generalData)  
    # Remove refill station
    update_total_score(total_score,scoredSolution,generalData,add=-1)
    solution_subgraph[LK.locations].pop(key) 
    return total, footfall

def initize_solution_subgraph(C, solution, total_score, mapEntity, generalData, mapName):
    """
    Reset solutions in a subgraph C
    1. Extract the mapEntity and solution from the subgraph
    2. Reset the subgraph solution by removing all refills stations in C
    3. Update the total score earned
    Returns
    ------    
    mapEntity_subgraph
        a subset of mapEntity in subgraph C
    solution_subgraph
        a subset of solution in subgraph C, resetted
    total_score[SK.total]
        total score updated
    """
    # inotilize subgraph data and solution
    mapEntity_subgraph = get_mapEntity_subgraph(mapEntity, C)
    solution_subgraph = get_solution_subgreaph(solution, C)  
    # Clear solution in subgraph
    if solution_subgraph[LK.locations]:
        #print("resetting total score")
        scoredSolution = calculateScore(mapName, solution_subgraph, mapEntity_subgraph, generalData)
        update_total_score(total_score,scoredSolution,generalData,add=-1)
        for key in solution_subgraph[LK.locations]:
            solution[LK.locations].pop(key)
        solution_subgraph = {LK.locations: dict()}
    return mapEntity_subgraph, solution_subgraph, total_score[SK.total]

def graph_mixed_score(mapEntity, generalData, mapName, maxK=1, maxL=4, maxB=1, reverse_task=True):
    """Main fucntion of our solution, a mix of beam-search and brute force algorithm
    1. Create graph, initilize total solution, total score and best total score
    2. Loop maxL times:
        1. get a list of disconnected subgraph
        2. For each subgraph:
            1. Intitalize mapEntity, solution and total score in the subgraph
            2. If subgraph size <= maxB, do brute force search for the best solution within the subgraph
            3. Else, do beam search with width maxK for the best solution within the subgraph
            4. add subgraph solution into total solution and update the total score 
    Returns
    ------    
    solution
        Total solution to be submitted         
    """
    G = create_graph(mapEntity, generalData)
    # Variables on solution and score
    solution = {LK.locations: dict()}
    total_score = {
        SK.co2Savings: 0,
        SK.totalFootfall: 0,
        SK.earnings: 0,
        SK.total: 0,
    }    
    best_total = 0
    for i in range(maxL):
        reverse = i%2 if reverse_task else False
        subgraphsss = sorted (nx.connected_components(G), key=lambda C: len(C), reverse=reverse)
        print("len")
        print([len(i) for i in subgraphsss if len(i)>=10])
        for C in subgraphsss: #reverse=reverse
            K = min(maxK, len(C))
            S = G.subgraph(C)
            mapEntity_subgraph, solution_subgraph, best_total = initize_solution_subgraph(C, solution, total_score, mapEntity, generalData, mapName)
            if len(C) <= maxB:
                 # Place refill station at each step
                solution_grid = dict()
                for node in C:
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
                L = [[(k, v) for v in vs] for k, vs in solution_grid.items()]
                solution_tmps = list(map(dict, itertools.product(*L)))
                best_solution = None
                for solution_tmp in solution_tmps:
                    solution_tmp = {k:v for k,v in solution_tmp.items() if v is not None}
                    if not solution_tmp:
                        continue
                    solution_tmp = {LK.locations: solution_tmp}
                    scoredSolution = calculateScore(mapName, solution_tmp, mapEntity_subgraph, generalData)
                    total = update_total_score(total_score,scoredSolution,generalData,add=1)
                    if total > best_total:
                        best_solution = solution_tmp
                        best_total = total
                    update_total_score(total_score,scoredSolution,generalData,add=-1)
                solution_subgraph = best_solution
            else:
                bestk = []
                heapq.heappush(bestk, KeyDict((0,0),{
                    LK.locations: dict(),
                    'terminated': False,
                } ))
                # Place refill station at each step
                steps = 0
                while True:
                    steps += 1
                    histories = copy.deepcopy(bestk)
                    for history in histories:
                        if history.dct['terminated']:
                            continue
                        history = history.dct
                        visited = set(history[LK.locations].keys())
                        for key in C-visited:
                            tmp_solution = None
                            tmp_total = 0
                            tmp_footfall = 0
                            for solution_test in [{LK.f9100Count: 1, LK.f3100Count: 0}, {LK.f9100Count: 0, LK.f3100Count: 1}]:
                                total, footfall = try_placing_refill(history, key, solution_test, total_score, mapEntity_subgraph, generalData, mapName)
                                if total > tmp_total:
                                    tmp_solution = solution_test
                                    tmp_total = total       
                                    tmp_footfall = footfall          
                            if tmp_total > best_total:
                                temp = copy.deepcopy(history)
                                temp[LK.locations][key] = tmp_solution
                                if len(bestk) < K:                            
                                    heapq.heappush(bestk, KeyDict((tmp_total,tmp_footfall),{
                                        LK.locations: temp[LK.locations],
                                        'terminated': False,
                                    }))
                                else:
                                    heapq.heappushpop(bestk, KeyDict((tmp_total,tmp_footfall),{
                                        LK.locations: temp[LK.locations],
                                        'terminated': False,
                                    }))
                    for best_solution in bestk:
                        if len(best_solution.dct[LK.locations]) < steps:
                            best_solution.dct['terminated'] = True
                    if all([best_solution.dct['terminated'] for best_solution in bestk]):
                        break
                solution_subgraph = heapq.nlargest(1,bestk)[0].dct
            
            if solution_subgraph and solution_subgraph[LK.locations]:
                # Place refill station in subgraph in solution
                solution[LK.locations].update(solution_subgraph[LK.locations])
                scoredSolution = calculateScore(mapName, solution_subgraph, mapEntity_subgraph, generalData)
                update_total_score(total_score,scoredSolution,generalData,add=1)
    return solution




def algo(name, mapEntity,  generalData, mapName, **args):
    """
    Interface for eval.py
    """
    func_map = {
        "graph_mixed_score":graph_mixed_score,
    }
    func = func_map[name]
    return func(mapEntity,  generalData, mapName, **args)