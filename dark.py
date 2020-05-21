# coding: utf-8

# Usage:
# python dark.py --latitude 48.8638 --longitude 2.4485 --elevation 97

import argparse
import datetime as dt
import json
from skyfield import almanac
from skyfield.api import Topos, load

COORDINATES_PRECISION = 4


def default_json_converter(obj):
    if isinstance(obj, dt.datetime):
        return obj.__str__()
    return None


arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--latitude")
arg_parser.add_argument("--longitude")
arg_parser.add_argument("--elevation")
args = arg_parser.parse_args()


# Figure out local midnight
zone = dt.timezone.utc
now = dt.datetime.now(tz=zone)
midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
next_midnight = midnight + dt.timedelta(days=1)

ts = load.timescale(builtin=True)
t0 = ts.utc(midnight)
t1 = ts.utc(next_midnight)
eph = load("de421.bsp")
observer_location = Topos(
    latitude_degrees=round(float(args.latitude), COORDINATES_PRECISION),
    longitude_degrees=round(float(args.longitude), COORDINATES_PRECISION),
    elevation_m=int(args.elevation),
)
f = almanac.dark_twilight_day(eph, observer_location)
times, events = almanac.find_discrete(t0, t1, f)

twilight_events = []

for t, e in zip(times, events):
    time = str(t.astimezone(zone))[:16]
    name = almanac.TWILIGHTS[e]
    twilight_events.append({"time": time, "name": name})

dumps = json.dumps(
    {"events": twilight_events}, indent=2, default=default_json_converter, ensure_ascii=False,
)

print(dumps)
