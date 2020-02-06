#!/usr/bin/env python3

# copyright 2019, MIT License.

# this script needs python3.6 or newer because of the "f-string" syntax,
# aka PEP 498's literal string interpolation. You'll also need to install
# several required modules: pip3 install -r requirements.txt
import collections
import datetime
import re
import sys

import requests
from geopy.distance import geodesic as geo

# Record for hotspot data
HotSpot = collections.namedtuple('HotSpot', 'name, dist, score, coord')


# helper funcs
def loc(d, prefix=''):
  return (d[f'{prefix}lat'], d[f'{prefix}lng'])


def normalize_name(n):
  return re.sub(r'\W', '-', n.lower())


# TODO: redo this a bit to take some params
def main():
  homeid = None
  if len(sys.argv) > 1:
    homeid = normalize_name(' '.join(sys.argv[1:]))
  else:
    print("give your hotspot id (one-two-three) as the argument. spaces or dashes are fine.")

  print(f"normalized name: {homeid}")

  home = None
  hotspot = {}
  r = requests.get('https://network.helium.com/fetchHotspots')
  for h in r.json():
    # save them by name
    stdname = normalize_name(h['name'])
    hotspot[stdname] = h
    if stdname == homeid:
      home = h

  if not home:
    print(f"eep, we didn't find your hotspot name ({homeid}).")
    sys.exit(-1)

  # TODO: In the future, maybe we dump this out to a file as a cache, and then
  # use it in activity.py
  neighbors = {}

  # now compare them to see if they're local
  print(f"{'dist':5} {'score':>6} {'hotspot name':35}")
  for h_id, h in hotspot.items():
    dist = geo(loc(home), loc(h)).miles
    if dist < 30:
      name = h['name']
      neighbors[name] = HotSpot(name=name,
                                dist=dist,
                                score=int(h['score'] * 100),
                                coord=f"{h['lat']:3.4f}, {h['lng']:3.4f}")

  # There's probably a more readable way to do this, like ValueSortedDict with
  # a `key` function, but I couldn't get it to work
  for name, v in sorted(neighbors.items(), reverse=True,
                        key=lambda item: item[1].dist):
    print(f"{v.dist:4.1f} {v.score:5} {name:35} {v.coord}")

  # now pull peeps who have witnessed us: https://tedder.me/lols/witness-me-2.gif
  witret = requests.get(f'https://explorer.helium.foundation/api/witnesses/{home["address"]}')
  data = witret.json().get('data')
  if len(data):
    print(f"\n{'hotspot name':30}{'dist':^5} {'count':^5} {'rssi':>6}{'witness time':^20}")
    for h in sorted(data, key=lambda x: x.get('recent_time')):
      # h = dict of pocs that saw us
      name = h['name']
      hist = h['hist']
      dist = '0.0' if name not in neighbors else neighbors[name].dist
      rssi = max(hist, key=hist.get)
      count = sum(hist.values())
      ts = datetime.datetime.fromtimestamp(h['recent_time'] / 1000**3).isoformat(timespec='minutes')
      print(f"{name:30} {dist:^4.1f} {count:>5} {rssi:>6}{ts:>20}")


if __name__ == '__main__':
  main()
