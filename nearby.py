#!/usr/bin/env python3

# copyright 2019, MIT License.

# this script needs python3.6 or newer because of the "f-string" syntax,
# aka PEP 498's literal string interpolation. you'll also need geopy and requests:
# pip3 install geopy requests

from geopy.distance import geodesic as geo
import re
import sys
import requests
import datetime

# helper funcs
def loc(d, prefix=''):
  return (d[f'{prefix}lat'], d[f'{prefix}lng'])
def normalize_name(n):
  return re.sub(r'\W', '-', n.lower())

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

results = []

# now compare them to see if they're local
print(f"dist score name")
for h_id,h in hotspot.items():
  dist = geo( loc(home), loc(h) ).miles
  if dist < 30:
    score = int(h['score']*100)
    coord = f"{h['lat']}, {h['lng']}"
    name = h['name']
    result = (dist, score, name, coord)
    results.append(result)

def sortDist(val): 
    return val[0] 

results.sort(key=sortDist)

for result in results:
  print(f"{result[0]:4.1f} {result[1]:5} {result[2]:30} {result[3]}")

# now pull peeps who have witnessed us: https://tedder.me/lols/witness-me-2.gif
witret = requests.get(f'https://explorer.helium.foundation/api/witnesses/{home["address"]}')
data = witret.json().get('data')
if len(data):
  print(f"\nhotspot name                   count  rssi recent time")
  for h in sorted(data, key=lambda x: x.get('recent_time')):
    # h = dict of pocs that saw us
    hist = h['hist']
    rssi = max(hist, key=hist.get)
    count = sum(hist.values())
    print(f"{h['name']:25} {count:10} {rssi:5} {datetime.datetime.fromtimestamp(h['recent_time']/1000**3).isoformat()}")


