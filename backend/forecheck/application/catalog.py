"""What Forecheck watches: the stations and the models it compares."""

from collections.abc import Sequence
from dataclasses import dataclass

from forecheck.domain.entities import Station
from forecheck.domain.types import ModelId, StationId


@dataclass(frozen=True, slots=True)
class ModelSpec:
    id: ModelId
    label: str
    # The name the forecast provider knows the model by.
    provider_name: str


@dataclass(frozen=True, slots=True)
class Catalog:
    stations: Sequence[Station]
    models: Sequence[ModelSpec]

    def __post_init__(self) -> None:
        station_ids = [station.id for station in self.stations]
        if len(set(station_ids)) != len(station_ids):
            raise ValueError("station ids must be unique")
        model_ids = [model.id for model in self.models]
        if len(set(model_ids)) != len(model_ids):
            raise ValueError("model ids must be unique")

    def station(self, station_id: StationId) -> Station | None:
        return next((station for station in self.stations if station.id == station_id), None)

    def model(self, model_id: ModelId) -> ModelSpec | None:
        return next((model for model in self.models if model.id == model_id), None)

    @property
    def provider_names(self) -> dict[ModelId, str]:
        return {model.id: model.provider_name for model in self.models}


# Coordinates are the town or airport of each IMGW synoptic station, to about a kilometre.
# The models grid is 9 to 28 km wide, so that is far finer than the forecast itself.
# To add a station, append it here: its IMGW id is in https://danepubliczne.imgw.pl/api/data/synop.
DEFAULT_CATALOG = Catalog(
    stations=(
        Station(StationId("12375"), "Warszawa", 52.166, 20.967),
        Station(StationId("12566"), "Kraków", 50.078, 19.785),
        Station(StationId("12424"), "Wrocław", 51.103, 16.886),
        Station(StationId("12330"), "Poznań", 52.421, 16.826),
        Station(StationId("12155"), "Gdańsk", 54.377, 18.466),
        Station(StationId("12465"), "Łódź", 51.722, 19.398),
        Station(StationId("12205"), "Szczecin", 53.395, 14.622),
        Station(StationId("12495"), "Lublin", 51.220, 22.400),
        Station(StationId("12560"), "Katowice", 50.241, 19.034),
        Station(StationId("12295"), "Białystok", 53.107, 23.162),
        Station(StationId("12580"), "Rzeszów", 50.110, 22.019),
        # IMGW has no synoptic station in Dębica. Tarnów is the nearest one, about 35 km west.
        Station(StationId("12575"), "Tarnów", 50.030, 20.990),
        Station(StationId("12195"), "Suwałki", 54.133, 22.950),
        Station(StationId("12625"), "Zakopane", 49.294, 19.962),
        Station(StationId("12135"), "Hel", 54.604, 18.809),
    ),
    models=(
        ModelSpec(ModelId("icon"), "ICON", "icon_seamless"),
        ModelSpec(ModelId("ecmwf"), "ECMWF", "ecmwf_ifs025"),
        ModelSpec(ModelId("gfs"), "GFS", "gfs_seamless"),
    ),
)
