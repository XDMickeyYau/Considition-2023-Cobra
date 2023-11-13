from dataclasses import dataclass


@dataclass
class MapNames:
    stockholm = "stockholm"
    goteborg = "goteborg"
    malmo = "malmo"
    uppsala = "uppsala"
    vasteras = "vasteras"
    orebro = "orebro"
    london = "london"
    linkoping = "linkoping"
    berlin = "berlin"
    sSandbox = "s-sandbox"
    gSandbox = "g-sandbox"


@dataclass
class LocationKeys:
    locations = "locations"
    locationName = "locationName"
    locationType = "locationType"
    footfall = "footfall"
    footfallScale = "footfallScale"
    salesVolume = "salesVolume"
    f3100Count = "freestyle3100Count"
    f9100Count = "freestyle9100Count"
    salesCapacity = "salesCapacity"
    leasingCost = "leasingCost"
    revenue = "revenue"
    co2Savings = "gramCo2Savings"


@dataclass
class HotspotKeys:
    spread = "spread"
    hotspots = "hotspots"


@dataclass
class MapKeys:
    border = "border"
    longitudeMax = "longitudeMax"
    longitudeMin = "longitudeMin"
    latitudeMax = "latitudeMax"
    latitudeMin = "latitudeMin"


@dataclass
class CoordinateKeys:
    latitude = "latitude"
    longitude = "longitude"


@dataclass
class ScoringKeys:
    gameId = "id"
    mapName = "mapName"
    gameScore = "gameScore"
    totalRevenue = "totalRevenue"
    totalF3100Count = "totalFreestyle3100Count"
    totalF9100Count = "totalFreestyle9100Count"
    co2Savings = "kgCo2Savings"
    totalFootfall = "totalFootfall"
    totalLeasingCost = "totalLeasingCost"
    gameScore = "gameScore"
    earnings = "earnings"
    total = "total"


@dataclass
class GeneralKeys:
    constantExpDistributionFunction = "constantExpDistributionFunction"
    willingnessToTravelInMeters = "willingnessToTravelInMeters"
    f3100Data = "freestyle3100Data"
    f9100Data = "freestyle9100Data"
    refillCapacityPerWeek = "refillCapacityPerWeek"
    leasingCostPerWeek = "leasingCostPerWeek"
    refillUnitData = "refillUnitData"
    classicUnitData = "classicUnitData"
    profitPerUnit = "profitPerUnit"
    co2PerUnitInGrams = "co2PerUnitInGrams"
    co2PricePerKiloInSek = "co2PricePerKiloInSek"
    locationTypes = "locationTypes"
    salesVol = "salesVolume"
    type_ = "type"
    refillDistributionRate = "refillDistributionRate"
    refillSalesFactor = "refillSalesFactor"
    staticCo2 = "staticCo2"
    groceryStoreLarge = "groceryStoreLarge"
    groceryStore = "groceryStore"
    convenience = "convenience"
    gasStation = "gasStation"
    kiosk = "kiosk"
