import math
from typing import Dict
import uuid
from data_keys import (
    LocationKeys as LK,
    CoordinateKeys as CK,
    GeneralKeys as GK,
    ScoringKeys as SK,
    HotspotKeys as HK,
    MapNames as MN,
    MapKeys as MK,
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

    if mapName not in [MN.sSandbox, MN.gSandbox]:
        locationListNoRefillStation = {}
        for key in mapEntity[LK.locations]:
            loc = mapEntity[LK.locations][key]
            if key in solution[LK.locations]:
                loc_player = solution[LK.locations][key]
                f3_count = loc_player[LK.f3100Count]
                f9_count = loc_player[LK.f9100Count]

                for f_count in [f3_count, f9_count]:
                    if f_count < 0 or f_count > 2:
                        raise SystemExit(
                            f"Max number of locations is 2 for each type of refill station. Remove or alter location: {key}"
                        )
                scoredSolution[LK.locations][key] = {
                    LK.locationName: loc[LK.locationName],
                    LK.locationType: loc[LK.locationType],
                    CK.latitude: loc[CK.latitude],
                    CK.longitude: loc[CK.longitude],
                    LK.footfall: loc[LK.footfall],
                    LK.f3100Count: f3_count,
                    LK.f9100Count: f9_count,
                    LK.salesVolume: loc[LK.salesVolume]
                    * generalData[GK.refillSalesFactor],
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
                    LK.salesVolume: loc[LK.salesVolume]
                    * generalData[GK.refillSalesFactor],
                }

        if not scoredSolution[LK.locations]:
            raise SystemExit(
                f"Error: No valid locations with refill stations were placed for map: {mapName}"
            )

        scoredSolution[LK.locations] = distributeSales(
            scoredSolution[LK.locations], locationListNoRefillStation, generalData
        )
    else:
        sandboxValidation(mapEntity, solution)
        scoredSolution[LK.locations] = initiateSandboxLocations(
            scoredSolution[LK.locations], generalData, solution
        )
        scoredSolution[LK.locations] = calcualteFootfall(
            scoredSolution[LK.locations], mapEntity
        )

    scoredSolution[LK.locations] = divideFootfall(
        scoredSolution[LK.locations], generalData
    )

    for key in scoredSolution[LK.locations]:
        loc = scoredSolution[LK.locations][key]
        loc[LK.salesVolume] = round(loc[LK.salesVolume], 0)
        sales = loc[LK.salesVolume]

        if loc[LK.footfall] <= 0 and mapName in [MN.sSandbox, MN.gSandbox]:
            sales = 0

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
        loc[LK.co2Savings] = (
            sales
            * (
                generalData[GK.classicUnitData][GK.co2PerUnitInGrams]
                - generalData[GK.refillUnitData][GK.co2PerUnitInGrams]
            )
            - loc[LK.f3100Count] * generalData[GK.f3100Data][GK.staticCo2]
            - loc[LK.f9100Count] * generalData[GK.f9100Data][GK.staticCo2]
        )
        scoredSolution[SK.gameScore][SK.co2Savings] += loc[LK.co2Savings] / 1000

        scoredSolution[SK.totalRevenue] += (
            sales * generalData[GK.refillUnitData][GK.profitPerUnit]
        )

        scoredSolution[SK.totalLeasingCost] += scoredSolution[LK.locations][key][
            LK.leasingCost
        ]

        scoredSolution[SK.gameScore][SK.totalFootfall] += (
            scoredSolution[LK.locations][key][LK.footfall] / 1000
        )

    scoredSolution[SK.totalRevenue] = round(scoredSolution[SK.totalRevenue], 2)

    scoredSolution[SK.gameScore][SK.co2Savings] = round(
        scoredSolution[SK.gameScore][SK.co2Savings], 2
    )

    scoredSolution[SK.gameScore][SK.totalFootfall] = round(
        scoredSolution[SK.gameScore][SK.totalFootfall], 4
    )

    scoredSolution[SK.gameScore][SK.earnings] = (
        scoredSolution[SK.totalRevenue] - scoredSolution[SK.totalLeasingCost]
    ) / 1000

    scoredSolution[SK.gameScore][SK.total] = round(
        (
            scoredSolution[SK.gameScore][SK.co2Savings]
            * generalData[GK.co2PricePerKiloInSek]
            + scoredSolution[SK.gameScore][SK.earnings]
        )
        * (1 + scoredSolution[SK.gameScore][SK.totalFootfall]),
        2,
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

    return round(d, 0)


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


def calcualteFootfall(locations, mapEntity):
    maxFootfall = 0
    for keyLoc in locations:
        loc = locations[keyLoc]
        for hotspot in mapEntity[HK.hotspots]:
            distanceInMeters = distanceBetweenPoint(
                hotspot[CK.latitude],
                hotspot[CK.longitude],
                loc[CK.latitude],
                loc[CK.longitude],
            )

            maxSpread = hotspot[HK.spread]
            if distanceInMeters <= maxSpread:
                val = hotspot[LK.footfall] * (1 - (distanceInMeters / maxSpread))
                loc[LK.footfall] += val / 10
        if maxFootfall < loc[LK.footfall]:
            maxFootfall = loc[LK.footfall]

    if maxFootfall > 0:
        for keyLoc in locations:
            loc = locations[keyLoc]
            if loc[LK.footfall] > 0:
                loc[LK.footfallScale] = int(loc[LK.footfall] / maxFootfall * 10)
                if loc[LK.footfallScale] < 1:
                    loc[LK.footfallScale] = 1
    return locations


def getSalesVolume(locationType, generalData):
    for key in generalData[GK.locationTypes]:
        locType = generalData[GK.locationTypes][key]
        if locationType == locType[GK.type_]:
            return locType[GK.salesVol]
    return 0


def initiateSandboxLocations(locations: list, generalData, solution):
    for key in solution[LK.locations]:
        loc_player = solution[LK.locations][key]
        sv = getSalesVolume(loc_player[LK.locationType], generalData)
        scoredSolution = {
            LK.footfall: 0,
            CK.longitude: loc_player[CK.longitude],
            CK.latitude: loc_player[CK.latitude],
            LK.f3100Count: loc_player[LK.f3100Count],
            LK.f9100Count: loc_player[LK.f9100Count],
            LK.locationType: loc_player[LK.locationType],
            LK.locationName: key,
            LK.salesVolume: sv,
            LK.salesCapacity: loc_player[LK.f3100Count]
            * generalData[GK.f3100Data][GK.refillCapacityPerWeek]
            + loc_player[LK.f9100Count]
            * generalData[GK.f9100Data][GK.refillCapacityPerWeek],
            LK.leasingCost: loc_player[LK.f3100Count]
            * generalData[GK.f3100Data][GK.leasingCostPerWeek]
            + loc_player[LK.f9100Count]
            * generalData[GK.f9100Data][GK.leasingCostPerWeek],
        }
        locations[key] = scoredSolution

    for key in locations:
        count = 1

        for keySurrounding in locations:
            if key != keySurrounding:
                distance = distanceBetweenPoint(
                    locations[key][CK.latitude],
                    locations[key][CK.longitude],
                    locations[keySurrounding][CK.latitude],
                    locations[keySurrounding][CK.longitude],
                )
                if distance < generalData[GK.willingnessToTravelInMeters]:
                    count += 1

        locations[key][LK.salesVolume] = locations[key][LK.salesVolume] / count

    return locations


def divideFootfall(locations, generalData):
    for key in locations:
        count = 1

        for keySurrounding in locations:
            if key != keySurrounding:
                distance = distanceBetweenPoint(
                    locations[key][CK.latitude],
                    locations[key][CK.longitude],
                    locations[keySurrounding][CK.latitude],
                    locations[keySurrounding][CK.longitude],
                )
                if distance < generalData[GK.willingnessToTravelInMeters]:
                    count += 1

        locations[key][LK.footfall] = locations[key][LK.footfall] / count

    return locations


def sandboxValidation(mapEntity, request):
    countGroceryStoreLarge = 0
    countGroceryStore = 0
    countConvenience = 0
    countGasStation = 0
    countKiosk = 0
    maxGroceryStoreLarge = 5
    maxGroceryStore = 20
    maxConvenience = 20
    maxGasStation = 8
    maxKiosk = 3

    totalStores = (
        maxGroceryStoreLarge
        + maxGroceryStore
        + maxConvenience
        + maxGasStation
        + maxKiosk
    )

    numberErrorMsg = f"locationName needs to start with 'location' and followed with a number larger than 0 and less than {totalStores + 1}."

    for locKey in request[LK.locations]:
        # Validate location name
        if str(locKey).startswith("location") == False:
            raise SystemExit(f"{numberErrorMsg} {locKey} is not a valid name")
        loc_num = locKey[8:]
        if not locKey:
            raise SystemExit(
                f"{numberErrorMsg} Nothing followed location in the locationName"
            )

        try:
            n = int(loc_num)
            if n <= 0 or n > totalStores:
                raise SystemExit(f"{numberErrorMsg} {n} is not within the constraints")
        except:
            raise SystemExit(f"{numberErrorMsg} {loc_num} is not a number")

        # Validate long and lat
        if (
            mapEntity[MK.border][MK.latitudeMin]
            > request[LK.locations][locKey][CK.latitude]
            or mapEntity[MK.border][MK.latitudeMax]
            < request[LK.locations][locKey][CK.latitude]
        ):
            raise SystemExit(
                f"Latitude is missing or out of bounds for location : {locKey}"
            )
        if (
            mapEntity[MK.border][MK.longitudeMin]
            > request[LK.locations][locKey][CK.longitude]
            or mapEntity[MK.border][MK.longitudeMax]
            < request[LK.locations][locKey][CK.longitude]
        ):
            raise SystemExit(
                f"Longitude is missing or out of bounds for location : {locKey}"
            )
        # Validate locationType

        t = request[LK.locations][locKey][LK.locationType]
        if not t:
            raise SystemExit(f"locationType is missing for location) : {locKey}")
        elif t == "Grocery-store-large":
            countGroceryStoreLarge += 1
        elif t == "Grocery-store":
            countGroceryStore += 1
        elif t == "Convenience":
            countConvenience += 1
        elif t == "Gas-station":
            countGasStation += 1
        elif t == "Kiosk":
            countKiosk += 1
        else:
            raise SystemExit(
                f"locationType --> {t} not valid (check GetGeneralGameData for correct values) for location : {locKey}"
            )
        # Validate that max number of location is not exceeded
        if (
            countGroceryStoreLarge > maxGroceryStoreLarge
            or countGroceryStore > maxGroceryStore
            or countConvenience > maxConvenience
            or countGasStation > maxGasStation
            or countKiosk > maxKiosk
        ):
            raise SystemExit(
                f"Number of allowed locations exceeded for locationType: {t}"
            )
