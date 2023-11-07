import math

from numpy import ndarray

from data_keys import (
    LocationKeys as LK,
    CoordinateKeys as CK,
    GeneralKeys as GK,
    ScoringKeys as SK,
)
import scoring
import uuid
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


# solution must have a dict with name of valid refill stations as key in solution[LK.locations]
def optimal_f3f9_count(solution, mapEntity, generalData) -> tuple[list, ndarray]:
    scoredSolution = {
        LK.locations: {}
    }
    locationListNoRefillStation = {}
    for key in mapEntity[LK.locations]:
        loc = mapEntity[LK.locations][key]
        if key in solution[LK.locations]:
            scoredSolution[LK.locations][key] = {
                LK.locationName: loc[LK.locationName],
                LK.locationType: loc[LK.locationType],
                CK.latitude: loc[CK.latitude],
                CK.longitude: loc[CK.longitude],
                LK.footfall: loc[LK.footfall],
                LK.salesVolume: loc[LK.salesVolume] * generalData[GK.refillSalesFactor]
            }
        else:
            locationListNoRefillStation[key] = {
                LK.locationName: loc[LK.locationName],
                LK.locationType: loc[LK.locationType],
                CK.latitude: loc[CK.latitude],
                CK.longitude: loc[CK.longitude],
                LK.footfall: loc[LK.footfall],
                LK.salesVolume: loc[LK.salesVolume] * generalData[GK.refillSalesFactor],
            }

    scoredSolution[LK.locations] = scoring.distributeSales(
        scoredSolution[LK.locations], locationListNoRefillStation, generalData
    )

    N = len(scoredSolution[LK.locations])
    NO_VAR = 3 * N
    NO_CONSTRAINTS = N
    MAX_F3F9_COUNT = 5
    keys_order, refill_sales_vol = [], []
    # total_footfall = 0
    for key in scoredSolution[LK.locations]:
        keys_order.append(key)
        refill_sales_vol.append(scoredSolution[LK.locations][key][LK.salesVolume])
        # total_footfall += scoredSolution[LK.locations][key][LK.footfall]
    co2_const_sales_withc = (generalData[GK.classicUnitData][GK.co2PerUnitInGrams] - generalData[GK.refillUnitData][GK.co2PerUnitInGrams]
                       ) * generalData[GK.co2PricePerKiloInSek] / 1000
    co2_const_f3_withc = generalData[GK.f3100Data][GK.staticCo2] * generalData[GK.co2PricePerKiloInSek] / 1000
    co2_const_f9_withc = generalData[GK.f9100Data][GK.staticCo2] * generalData[GK.co2PricePerKiloInSek] / 1000

    b_l = np.zeros(N)
    b_u = np.full_like(b_l, math.inf)
    A = np.zeros((NO_CONSTRAINTS, NO_VAR))
    for i in range(N):
        A[i][i * 2] = generalData[GK.f3100Data][GK.refillCapacityPerWeek]                 # f3100count_i
        A[i][i * 2 + 1] = generalData[GK.f9100Data][GK.refillCapacityPerWeek]             # f9100count_i
        A[i][i + 2 * N] = -1                                                              # fulfilled_saled_i
    constraints = LinearConstraint(A, b_l, b_u)

    c = np.empty(NO_VAR)
    integrality = np.empty(NO_VAR)
    l = np.zeros(NO_VAR)
    u = np.empty(NO_VAR)
    for i in range(2 * N):
        u[i] = MAX_F3F9_COUNT
        integrality[i] = 1
        if i % 2:
            c[i] = co2_const_f9_withc + generalData[GK.f9100Data][GK.leasingCostPerWeek]  # max(fx) = -min(-fx)
        else:
            c[i] = co2_const_f3_withc + generalData[GK.f3100Data][GK.leasingCostPerWeek]
    for i in range(2 * N, NO_VAR):
        u[i] = refill_sales_vol[i - 2 * N]
        integrality[i] = 0
        c[i] = - generalData[GK.refillUnitData][GK.profitPerUnit] - co2_const_sales_withc
    bounds = Bounds(l, u)

    results = milp(c=c, integrality=integrality, constraints=constraints, bounds=bounds)
    return (keys_order, results.x)
