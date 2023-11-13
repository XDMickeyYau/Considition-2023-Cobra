import math

from numpy import ndarray

from data_keys import (
    LocationKeys as LK,
    CoordinateKeys as CK,
    GeneralKeys as GK,
)
import scoring
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


# solution must have a dict with name of valid refill stations as key in solution[LK.locations]
def optimal_f3f9_count(solution, mapEntity, generalData) -> tuple[list, ndarray]:
    """Find optimal f3 and f9 counts for a possible set of placement of refill stations using linear programming."""

    # (mostly) same as scoring.calculateScore
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

    # State constant coefficients
    N = len(scoredSolution[LK.locations])
    NO_VAR = 3 * N
    NO_CONSTRAINTS = 2 * N
    MAX_F3F9_COUNT = 5
    keys_order, refill_sales_vol = [], []
    # total_footfall = 0                                                            # for printing score
    for key in scoredSolution[LK.locations]:
        keys_order.append(key)
        refill_sales_vol.append(scoredSolution[LK.locations][key][LK.salesVolume])
        # total_footfall += scoredSolution[LK.locations][key][LK.footfall]
    co2_const_sales_withc = (generalData[GK.classicUnitData][GK.co2PerUnitInGrams] - generalData[GK.refillUnitData][GK.co2PerUnitInGrams]
                       ) * generalData[GK.co2PricePerKiloInSek] / 1000
    co2_const_f3_withc = generalData[GK.f3100Data][GK.staticCo2] * generalData[GK.co2PricePerKiloInSek] / 1000
    co2_const_f9_withc = generalData[GK.f9100Data][GK.staticCo2] * generalData[GK.co2PricePerKiloInSek] / 1000

    # construct constraints: (f3count_i)*cap3 + (f9count_i)*cap9 >= ful_sales_i for i from 1 to n = no of refill station
    #                        f3count_i + f9count_i >= 1 for i from 1 to n
    b_l = np.append(np.zeros(N), np.ones(N))
    b_u = np.full_like(b_l, math.inf)
    A = np.zeros((NO_CONSTRAINTS, NO_VAR))
    for i in range(N):
        A[i][i * 2] = generalData[GK.f3100Data][GK.refillCapacityPerWeek]                 # f3100count_i
        A[i][i * 2 + 1] = generalData[GK.f9100Data][GK.refillCapacityPerWeek]             # f9100count_i
        A[i][i + 2 * N] = -1                                                              # fulfilled_saled_i
    for i in range(N, 2 * N):
        A[i][(i - N) * 2] = A[i][(i - N) * 2 + 1] = 1
    constraints = LinearConstraint(A, b_l, b_u)

    # construct bounds: 0 <= f3count_i, f9count_i <= 5 for i from 1 to n
    #                   0 <= ful_sales_i <= sales_vol_i for i from 1 to n
    # construct cost vector -f(x) where f(x) is:
    #   sum(ful_sales_i * profitPerUnit - (f3count_i)*cost3 - (f9count_i)*cost10)
    #   + sum((ful_sales_i)*cs*c - (f3count_i)*c3*c - (f9count_i)*c9*c)
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
    # print simulated score to see how close it is to the real score
    # print(results.fun * (1 + total_footfall))
    return (keys_order, results.x)
