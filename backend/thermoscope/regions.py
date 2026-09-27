"""Bounded pilot configurations; these are not facility or incident labels."""

from datetime import date, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Product(StrEnum):
    NOAA20 = "VIIRS_NOAA20_NRT"
    NOAA21 = "VIIRS_NOAA21_NRT"
    SNPP = "VIIRS_SNPP_NRT"
    NOAA20_SP = "VIIRS_NOAA20_SP"  # standard-processing archive; FIRMS keeps it before NRT starts


SATELLITES = {
    Product.NOAA20: "N20",
    Product.NOAA21: "N21",
    Product.SNPP: "N",
    Product.NOAA20_SP: "N20",
}
# One sensor stream for grouping and history: FIRMS serves NOAA-20 SP up to the day before
# NOAA-20 NRT begins, so the two products do not overlap in time (checked via data_availability).
NOAA20_FAMILY = "VIIRS_NOAA20"
NOAA20_PRODUCTS = (Product.NOAA20.value, Product.NOAA20_SP.value)


class Bounds(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False, extra="forbid")
    west: float = Field(ge=-180, le=180)
    south: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)

    @model_validator(mode="after")
    def bounded_area(self):
        if not 0 < self.east - self.west <= 5 or not 0 < self.north - self.south <= 5:
            raise ValueError("bounds must span more than zero and at most five degrees per axis")
        return self

    @classmethod
    def parse(cls, value: str):
        values = value.split(",")
        if len(values) != 4:
            raise ValueError("bbox requires west,south,east,north")
        return cls(**dict(zip(("west", "south", "east", "north"), values, strict=True)))

    def csv(self) -> str:
        return ",".join(str(v) for v in self.model_dump().values())

    def contains(self, lon: float, lat: float) -> bool:
        return self.west <= lon <= self.east and self.south <= lat <= self.north


class Window(BaseModel):
    product: Product = Product.NOAA20
    bounds: Bounds
    start_date: date
    days: int = Field(ge=1, le=5)

    @property
    def end_date(self) -> date:
        return self.start_date + timedelta(days=self.days - 1)


REGIONS = [
    {"id": "jamnagar", "name": "Jamnagar", "bbox": "69.5,22,70.5,23"},
    {"id": "singrauli", "name": "Singrauli", "bbox": "82,23.5,83,24.5"},
    {"id": "punjab", "name": "Punjab comparison", "bbox": "74.5,30,75.5,31"},
    # P05 additions: chosen for known industrial, mining, agricultural or forest activity so
    # that reviewed cases can cover several classes. Names describe places, not labels.
    {"id": "jharia", "name": "Jharia–Dhanbad", "bbox": "86,23.5,87,24.5"},
    {"id": "korba", "name": "Korba", "bbox": "82,22,83,23"},
    {"id": "talcher", "name": "Talcher–Angul", "bbox": "84.5,20.5,85.5,21.5"},
    {"id": "paradip", "name": "Paradip", "bbox": "86,19.8,87,20.8"},
    {"id": "mathura", "name": "Mathura", "bbox": "77.2,27,78.2,28"},
    {"id": "panipat", "name": "Panipat", "bbox": "76.5,29,77.5,30"},
    {"id": "vizag", "name": "Visakhapatnam", "bbox": "82.8,17.2,83.8,18.2"},
    {"id": "mumbai", "name": "Mumbai–Trombay", "bbox": "72.5,18.6,73.5,19.6"},
    {"id": "haldia", "name": "Haldia", "bbox": "87.6,21.6,88.6,22.6"},
    {"id": "simlipal", "name": "Simlipal", "bbox": "85.8,21.4,86.8,22.4"},
    {"id": "kgbasin", "name": "Krishna–Godavari basin", "bbox": "81.5,16,82.5,17"},
]
