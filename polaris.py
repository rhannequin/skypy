# coding: utf-8

# Usage:
# python polaris.py --latitude 48.8638 --longitude 2.4485 --elevation 97 \
# --datetime "2020-05-11 14:00:00"

import argparse
from datetime import datetime
import json
from skyfield.api import Angle, Star, Topos, load, utc
from skyfield.data import hipparcos
from utils.json_converter import json_converter
from utils.right_ascension_presenter import right_ascension_presenter
from utils.declination_presenter import declination_presenter
import utils.constants

with load.open(hipparcos.URL) as f:
    df = hipparcos.load_dataframe(f)


HYP_POLARIS_IDENTIFIER = 11767


arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--latitude")
arg_parser.add_argument("--longitude")
arg_parser.add_argument("--elevation")
arg_parser.add_argument("--datetime")
args = arg_parser.parse_args()

polaris = Star.from_dataframe(df.loc[HYP_POLARIS_IDENTIFIER])
polaris_ra = polaris.ra
polaris_dec = polaris.dec

eph = load("de421.bsp")
earth = eph["earth"]

ts = load.timescale(builtin=True)
observation_datetime = datetime.strptime(args.datetime, utils.constants.DATETIME_FORMAT).replace(
    tzinfo=utc
)
observation_time = ts.utc(observation_datetime)

observer_topos = Topos(
    latitude_degrees=round(float(args.latitude), utils.constants.COORDINATES_PRECISION),
    longitude_degrees=round(float(args.longitude), utils.constants.COORDINATES_PRECISION),
    elevation_m=int(args.elevation),
)
observer_location = earth + observer_topos
position = observer_location.at(observation_time)

astrometric = position.observe(polaris)
ra, dec, distance = astrometric.radec(epoch=ts.now())
hour_angle = Angle(hours=(observation_time.gast - ra.hours).item())

dumps = json.dumps(
    {
        "right_ascension": right_ascension_presenter(ra),
        "declination": declination_presenter(dec),
        "hour_angle": hour_angle.hstr(),
        "J2000": {
            "right_ascension": right_ascension_presenter(polaris_ra),
            "declination": declination_presenter(dec),
        },
    },
    indent=2,
    default=json_converter,
    ensure_ascii=False,
)

print(dumps)
