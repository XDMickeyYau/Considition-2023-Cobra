import math
from typing import Dict
import uuid
from data_keys import (
    LocationKeys as LK,
    CoordinateKeys as CK,
    GeneralKeys as GK,
    ScoringKeys as SK,
)


def calculateScore(mapName, solution, mapEntity, generalData):
    scoredSolution = {
        SK.gameId: str(uuid.uuid4()),
        SK.mapName: mapName,
        LK.locations: {},
        SK.gameScore: {SK.co2Savings: 0.0, SK.totalFootfall: 0.0},
        SK.totalRevenue: 0.0,
        SK.totalLeasingCost: 0.0,
        SK.totalF3100Count: 0,
        SK.totalF9100Count: 0,
    }

    locationListNoRefillStation = {}
    for key in mapEntity[LK.locations]:
        loc = mapEntity[LK.locations][key]
        if key in solution[LK.locations]:
            loc_player = solution[LK.locations][key]
            f3_count = loc_player[LK.f3100Count]
            f9_count = loc_player[LK.f9100Count]

            scoredSolution[LK.locations][key] = {
                LK.locationName: loc[LK.locationName],
                LK.locationType: loc[LK.locationType],
                CK.latitude: loc[CK.latitude],
                CK.longitude: loc[CK.longitude],
                LK.footfall: loc[LK.footfall],
                LK.f3100Count: f3_count,
                LK.f9100Count: f9_count,
                LK.salesVolume: loc[LK.salesVolume] * generalData[GK.refillSalesFactor],
                LK.salesCapacity: f3_count
                * generalData[GK.f3100Data][GK.refillCapacityPerWeek]
                + f9_count * generalData[GK.f9100Data][GK.refillCapacityPerWeek],
                LK.leasingCost: f3_count
                * generalData[GK.f3100Data][GK.leasingCostPerWeek]
                + f9_count * generalData[GK.f9100Data][GK.leasingCostPerWeek],
            }

            if scoredSolution[LK.locations][key][LK.salesCapacity] <= 0:
                raise SystemExit(
                    f"You are not allowed to submit locations with no refill stations. Remove or alter location: {scoredSolution[LK.locations][key][LK.locationName]}"
                )
        else:
            locationListNoRefillStation[key] = {
                LK.locationName: loc[LK.locationName],
                LK.locationType: loc[LK.locationType],
                CK.latitude: loc[CK.latitude],
                CK.longitude: loc[CK.longitude],
                LK.footfall: loc[LK.footfall],
                LK.salesVolume: loc[LK.salesVolume] * generalData[GK.refillSalesFactor],
            }

    if not scoredSolution[LK.locations]:
        raise SystemExit(
            f"Error: No valid locations with refill stations were placed for map: {mapName}"
        )

    scoredSolution[LK.locations] = distributeSales(
        scoredSolution[LK.locations], locationListNoRefillStation, generalData
    )

    for key in scoredSolution[LK.locations]:
        loc = scoredSolution[LK.locations][key]
        loc[LK.salesVolume] = round(loc[LK.salesVolume], 0)
        sales = loc[LK.salesVolume]
        if loc[LK.salesCapacity] < loc[LK.salesVolume]:
            sales = loc[LK.salesCapacity]

        loc[LK.revenue] = sales * generalData[GK.refillUnitData][GK.profitPerUnit]
        loc[SK.earnings] = loc[LK.revenue] - loc[LK.leasingCost]

        scoredSolution[SK.totalF3100Count] += scoredSolution[LK.locations][key][
            LK.f3100Count
        ]
        scoredSolution[SK.totalF9100Count] += scoredSolution[LK.locations][key][
            LK.f9100Count
        ]

        scoredSolution[SK.gameScore][SK.co2Savings] += (
            sales
            * (
                generalData[GK.classicUnitData][GK.co2PerUnitInGrams]
                - generalData[GK.refillUnitData][GK.co2PerUnitInGrams]
            )
            / 1000
        )

        scoredSolution[SK.totalRevenue] += (
            sales * generalData[GK.refillUnitData][GK.profitPerUnit]
        )

        scoredSolution[SK.totalLeasingCost] += scoredSolution[LK.locations][key][
            LK.leasingCost
        ]

        scoredSolution[SK.gameScore][SK.totalFootfall] += scoredSolution[LK.locations][
            key
        ][LK.footfall]

    scoredSolution[SK.totalRevenue] = round(scoredSolution[SK.totalRevenue], 0)
    scoredSolution[SK.gameScore][SK.co2Savings] = round(
        scoredSolution[SK.gameScore][SK.co2Savings]
        - scoredSolution[SK.totalF3100Count]
        * generalData[GK.f3100Data][GK.staticCo2]
        / 1000
        - scoredSolution[SK.totalF9100Count]
        * generalData[GK.f9100Data][GK.staticCo2]
        / 1000,
        0,
    )

    scoredSolution[SK.gameScore][SK.earnings] = (
        scoredSolution[SK.totalRevenue] - scoredSolution[SK.totalLeasingCost]
    )

    scoredSolution[SK.gameScore][SK.total] = round(
        (
            scoredSolution[SK.gameScore][SK.co2Savings]
            * generalData[GK.co2PricePerKiloInSek]
            + scoredSolution[SK.gameScore][SK.earnings]
        )
        * (1 + scoredSolution[SK.gameScore][SK.totalFootfall]),
        0,
    )

    return scoredSolution


def distanceBetweenPoint(lat_1, long_1, lat_2, long_2) -> int:
    R = 6371e3
    φ1 = lat_1 * math.pi / 180  #  φ, λ in radians
    φ2 = lat_2 * math.pi / 180
    Δφ = (lat_2 - lat_1) * math.pi / 180
    Δλ = (long_2 - long_1) * math.pi / 180

    a = math.sin(Δφ / 2) * math.sin(Δφ / 2) + math.cos(φ1) * math.cos(φ2) * math.sin(
        Δλ / 2
    ) * math.sin(Δλ / 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    d = R * c

    return int(round(d, 0))


def distributeSales(with_, without, generalData):
    for key_without in without:
        distributeSalesTo = {}
        loc_without = without[key_without]

        for key_with_ in with_:
            distance = distanceBetweenPoint(
                loc_without[CK.latitude],
                loc_without[CK.longitude],
                with_[key_with_][CK.latitude],
                with_[key_with_][CK.longitude],
            )
            if distance < generalData[GK.willingnessToTravelInMeters]:
                distributeSalesTo[with_[key_with_][LK.locationName]] = distance

        total = 0
        if distributeSalesTo:
            for key_temp in distributeSalesTo:
                distributeSalesTo[key_temp] = (
                    math.pow(
                        generalData[GK.constantExpDistributionFunction],
                        generalData[GK.willingnessToTravelInMeters]
                        - distributeSalesTo[key_temp],
                    )
                    - 1
                )
                total += distributeSalesTo[key_temp]

            for key_temp in distributeSalesTo:
                with_[key_temp][LK.salesVolume] += (
                    distributeSalesTo[key_temp]
                    / total
                    * generalData[GK.refillDistributionRate]
                    * loc_without[LK.salesVolume]
                )

    return with_
