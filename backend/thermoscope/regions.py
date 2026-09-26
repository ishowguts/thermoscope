"""Bounded pilot configurations; these are not facility or incident labels."""

from datetime import date, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Product(StrEnum):
    NOAA20 = "VIIRS_NOAA20_NRT"
    NOAA21 = "VIIRS_NOAA21_NRT"
    SNPP = "VIIRS_SNPP_NRT"


SATELLITES = {Product.NOAA20: "N20", Product.NOAA21: "N21", Product.SNPP: "N"}


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
]
