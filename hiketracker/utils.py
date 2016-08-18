import re
from geolite2 import geolite2
import string
import random


def get_ip_addr(request):
    try:
        return request.headers["X_FORWARDED_FOR"].split(",")[0].strip()
    except KeyError:
        try:
            return request.headers["REMOTE_ADDR"]
        except KeyError:
            return request.remote_addr


def get_curr_loc(ip_address):
    reader = geolite2.reader()
    print(reader)
    curr_loc = reader.get(ip_address)
    if curr_loc:
        return {'lat': curr_loc['location']['latitude'], 'lng': curr_loc['location']['longitude']}
    else:
        # in honor of the application being created in NYC
        return {'lat': 40.7143, 'lng': -74.006}


def url_latlng_to_point(url_latlng):
    return 'SRID=4326;POINT(' + (' ').join(url_latlng.split(',')) + ')'


def url_latlng_to_dict(url_latlng):
    latlng_arr = url_latlng.split(',')
    return {'lat': float(latlng_arr[0]), 'lng': float(latlng_arr[1])}


def latlngarr_to_linestring(latlngarr):
    return "SRID=4326;LINESTRING(" + ",".join([latlng_to_pair(x) for x in latlngarr]) + ")"

# given a latlng dict (pair of lat and lng values), returns a string representation without comma
def latlng_to_pair(latlng):
    return str(latlng["lat"]) + " " + str(latlng["lng"])

def linestring_to_latlngarr(linestring):
    pairs_str = re.match(r'LINESTRING\((.*)\)', linestring).group(1)
    pairs_arr = pairs_str.split(',')
    # inner = re.match(r"^{(.*)}$", value).group(1)
    # return inner.split(",") if inner else []
    latlng_arr = [pair_to_latlng(pair) for pair in pairs_arr]
    return latlng_arr

def pair_to_latlng(pair):
    pair_arr = pair.split(' ')
    return {'lat': pair_arr[0], 'lng': pair_arr[1]}

# takes dict of lat lang coordinate; returns POINT(lat lng)
def latlng_to_point(latlng):
    return "SRID=4326;POINT(" + latlng_to_pair(latlng) + ")"


# convert length from (user's concept of) "miles" into units
# (1mile x(5280ft/1mile)x(515units/486ft) = 5595.06 units)
def miles_to_units(miles):
    return miles * 5595.06

def units_to_miles(units):
    return units / 5595.06


#returns list of random colors of length num_colors
def get_color_list(num_colors):
    return ['#'+ "".join([random.choice(string.hexdigits) for _ in range(3)]) for _ in range(num_colors)]
