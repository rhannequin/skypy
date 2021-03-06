# coding: utf-8

# Usage:
# python iss.py --latitude 48.8638 --longitude 2.4485 --elevation 97 \
# --pressure 0 --horizon 00:00 --step 60

import argparse
from datetime import timedelta
import json
import math
import ephem
from utils.json_converter import json_converter

AU_IN_KM = 149597871
MAXIMUM_VISIBLE_MAGNITUDE = -0.5


def get_magnitude(light_source, target):
    # Credits to Liam Kennedy
    # https://stackoverflow.com/questions/19759501/calculating-the-phase-angle-\
    # between-the-sun-iss-and-an-observer-on-the-earth

    a = light_source.earth_distance * AU_IN_KM - ephem.earth_radius
    b = target.range / 1000
    angle_c = ephem.separation((target.az, target.alt), (light_source.az, light_source.alt))
    c = math.sqrt(math.pow(a, 2) + math.pow(b, 2) - 2 * a * b * math.cos(angle_c))
    angle_a = math.acos((math.pow(b, 2) + math.pow(c, 2) - math.pow(a, 2)) / (2 * b * c))
    return (
        -1.3
        - 15
        + 5 * math.log10(target.range / 1000)
        - 2.5 * math.log10(math.sin(angle_a) + ((math.pi - angle_a) * math.cos(angle_a)))
    )


def pass_not_visible(start_time, end_time, light_source, target):
    all_pass_events = generate_events_list(start_time, end_time, light_source, target, step=1)
    result = list(
        map(
            lambda event: not event["eclipsed"] and event["magnitude"] < MAXIMUM_VISIBLE_MAGNITUDE,
            all_pass_events,
        )
    )
    return True not in result


def generate_events_list(start_time, end_time, light_source, target, step):
    times = []
    # We set the current time to the very first beginning of the pass
    current_time = start_time.datetime()

    # Loop from the very beginning to the very last moment of the event
    while current_time < end_time.datetime():
        times.append(current_time)
        current_time = current_time + timedelta(0, step)

    events_list = []

    # For every intervalle of time from the start to the end of the event,
    # get ISS information
    for time in times:
        event = generate_event(time, target, light_source)
        events_list.append(event)

    return events_list


def generate_event(event_time, target, light_source):
    obs.date = event_time
    light_source.compute(obs)
    target.compute(obs)
    return {
        "hour": event_time,
        "altitude": target.alt,
        "azimuth": target.az,
        "magnitude": get_magnitude(light_source, target),
        "distance_from_earth": target.range / 1000,
        "eclipsed": target.eclipsed,
        "sun_altitude": light_source.alt,
    }


arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--latitude")
arg_parser.add_argument("--longitude")
arg_parser.add_argument("--elevation")
arg_parser.add_argument("--pressure")
arg_parser.add_argument("--horizon")
arg_parser.add_argument("--step")
args = arg_parser.parse_args()

iss = ephem.readtle(
    "ISS",
    "1 25544U 98067A   20124.51596176  .00016717  00000-0  10270-3 0  9040",
    "2 25544  51.6426 209.5696 0001578 232.9055 127.1951 15.49338516 25086",
)

sun = ephem.Sun()
obs = ephem.Observer()
obs.lat = args.latitude
obs.long = args.longitude
obs.elevation = int(args.elevation)
obs.pressure = int(args.pressure)
obs.horizon = args.horizon

rendered_next_visible = False

# As long as we don't have a visible pass
while not rendered_next_visible:

    obs.date = obs.date.datetime()
    # We get the next pass from the current date
    rise_time, _, maximum_altitude_time, _, set_time, _ = obs.next_pass(iss)

    # We set the current date at the pass' maximum altitude time
    # to ensure we check if the pass is visible from the middle of the event
    obs.date = maximum_altitude_time.datetime()
    iss.compute(obs)
    sun.compute(obs)
    mag = get_magnitude(sun, iss)

    # We check if the pass is visible or not: ISS eclipsed or magnitude not high
    # enough

    if pass_not_visible(rise_time, set_time, sun, iss):
        # The pass is not visible, we set the current date to right after the
        # pass is finished to get a new one from the loop
        obs.date = set_time.datetime()
        continue

    # This pass is visible, let's get all the information

    rendered_next_visible = True

    events = generate_events_list(rise_time, set_time, sun, iss, step=int(args.step))

    dumps = json.dumps(
        {
            "longitude": obs.long,
            "latitude": obs.lat,
            "elevation": obs.elevation,
            "pressure": obs.pressure,
            "main_events": {
                "rise": generate_event(rise_time.datetime(), iss, sun),
                # CHECK THIS VALUE, NOT SURE IF CORRECT
                "maximum": generate_event(maximum_altitude_time.datetime(), iss, sun),
                "set": generate_event(set_time.datetime(), iss, sun),
            },
            "events": events,
        },
        indent=2,
        default=json_converter,
    )

    print(dumps)

# Sun altitude -14:46:57.4 => Degrees minutes seconds
# Sun altitude -0.2580050528049469 => radians


# import argparse
# import datetime as dt
# import json
# from skyfield.api import Topos, load, utc
# from utils.json_converter import json_converter
# import utils.constants

# ISS_TLE_IDENTIFIER = "ISS (ZARYA)"
# RISE_EVENT = 0
# CULMINATE_EVENT = 1
# SET_EVENT = 2

# arg_parser = argparse.ArgumentParser()
# arg_parser.add_argument("--latitude")
# arg_parser.add_argument("--longitude")
# arg_parser.add_argument("--elevation")
# arg_parser.add_argument("--start_datetime")
# arg_parser.add_argument("--end_datetime")
# arg_parser.add_argument("--step")
# args = arg_parser.parse_args()

# stations_url = "http://celestrak.com/NORAD/elements/stations.txt"
# satellites = load.tle_file(stations_url)
# by_name = {sat.name: sat for sat in satellites}
# satellite = by_name[ISS_TLE_IDENTIFIER]

# ts = load.timescale(builtin=True)
# start_time = ts.utc(
#     dt.datetime.strptime(args.start_datetime, utils.constants.DATETIME_FORMAT).replace(tzinfo=utc)
# )
# end_time = ts.utc(
#     dt.datetime.strptime(args.end_datetime, utils.constants.DATETIME_FORMAT).replace(tzinfo=utc)
# )

# eph = load("de421.bsp")
# earth = eph["earth"]
# observer_topos = Topos(
#     latitude_degrees=round(float(args.latitude), utils.constants.COORDINATES_PRECISION),
#     longitude_degrees=round(float(args.longitude), utils.constants.COORDINATES_PRECISION),
#     elevation_m=int(args.elevation),
# )

# times, events = satellite.find_events(observer_topos, start_time, end_time, altitude_degrees=10.0)
# print(times)
# print(events)

# dumps = {"events": []}

# events_length = len(events)
# if events_length > 0:
#     full_passes = []
#     i = 0
#     while i < events_length:
#         if (
#             (events[i] == RISE_EVENT)
#             and ((i + 1) < events_length)
#             and ((i + 2) < events_length)
#             and (events[i + 1] == CULMINATE_EVENT)
#             and (events[i + 2] == SET_EVENT)
#         ):
#             full_passes.append([times[i], times[i + 1], times[i + 2]])
#             i += 2

#         i += 1

#     if len(full_passes) > 0:
#         next_visible_pass = None

#         for full_pass in full_passes:
#             rise_datetime = full_pass[0].utc_datetime()
#             thirty_minutes = ts.utc(
#                 rise_datetime.year,
#                 rise_datetime.month,
#                 rise_datetime.day,
#                 rise_datetime.hour,
#                 range(0, 30, 1),
#             )
#             sunlit = satellite.at(thirty_minutes).is_sunlit(eph)
#             print(True in sunlit)

# print(json.dumps(dumps, indent=2, default=json_converter,))
