#!/usr/bin/env python3

# copyright 2019, MIT License.

# this script needs python3.6 or newer because of the "f-string" syntax,
# aka PEP 498's literal string interpolation. you'll also requests:
# pip3 install geopy requests
import re
import sys
from datetime import datetime, timezone

import requests
from geopy.distance import geodesic as geo


def safe_name_from_address(hotspot_address_map, address):
  h = hotspot_address_map.get(address)
  if not h: return ''
  return normalize_name(h['name'])


def get_challenge(home, challenge_id, hotspot_address_map):
  hotspot_address = home['address']
  challenge_activity = requests.get(f'https://explorer.helium.foundation/api/challenges/{challenge_id}')
  path = challenge_activity.json()['data']['pathElements']
  print("  result     witnesses  distance path     target                    receipt?")
  for i, elem in enumerate(path):
    if home['address'] == elem['address']:
      # even if these two are the same the lat/lon may not be equal. yay for floats and rounding.
      dist_txt = "   ----"
    else:
      dist = geo(loc(home), loc(elem)).miles
      dist_txt = f"{dist:7.2f}"
    tgt = safe_name_from_address(hotspot_address_map, elem['address'])
    rct_tgt = safe_name_from_address(hotspot_address_map, elem['receipt'].get('address'))
    receipt_label = "not received"
    if rct_tgt == tgt:
      receipt_label = "received"

    print(f"  {elem['result']:10} {len(elem['witnesses']):5}      {dist_txt}  {elem['receipt'].get('origin', ''):8} {tgt:25} {receipt_label}")


def get_activity(home, hotspot_map):
  hotspot_address = home['address']
  activity = requests.get(f'https://explorer.helium.foundation/api/hotspots/{hotspot_address}/activity')
  data = activity.json().get('data')
  if not len(data):
    print("no activity in the API for you.")
    return

  for a in reversed(data):
    reward_type = a['reward_type']
    witness_id = a['poc_witness_challenge_id']
    challenge_req_hash = a['poc_req_txn_hash']
    challenge_hash = a['poc_rx_txn_hash']
    id_spacing = ''

    if reward_type is not None and reward_type.startswith('poc'):
      block_id = a['reward_block_height']
      reward_amount = a['reward_amount'] / 100000000
      reward_time = format_time(a['reward_block_time'])

      if reward_type == 'poc_challengers':
        print(f"{reward_time}: Block {block_id} - {id_spacing:9} Mined {reward_amount} - Challenger")
      elif reward_type == 'poc_challengees':
        print(f"{reward_time}: Block {block_id} - {id_spacing:9} Mined {reward_amount} - Challengee")
      elif reward_type == 'poc_witnesses':
        print(f"{reward_time}: Block {block_id} - {id_spacing:9} Mined {reward_amount} - Witness")
    elif witness_id is not None:
      witness_time = format_time(a['poc_rx_txn_block_time'])
      block_id = a['poc_rx_txn_block_height']
      print(f"{witness_time}: Block {block_id} - {witness_id:7} - Challenge Witnessed")
    elif challenge_req_hash is not None:
      challenge_time = format_time(a['poc_req_txn_block_time'])
      block_id = a['poc_req_txn_block_height']
      print(f"{challenge_time}: Block {block_id} - {id_spacing:9} Challenge Constructed")
    elif challenge_hash is not None:
      challenge_time = format_time(a['poc_rx_txn_block_time'])
      block_id = a['poc_rx_txn_block_height']
      challenge_id = a['poc_rx_challenge_id']
      print(f"{challenge_time}: Block {block_id} - {challenge_id:7} - Challenge Success")
      get_challenge(home, challenge_id, hotspot_map)
    else:
      print("Unknown")


# Given a unix timestamp format it into an RFC3339 string in the  local time zone
def format_time(timestamp):
  return (
      datetime.fromtimestamp(timestamp, tz=timezone.utc)
      .astimezone()
      .isoformat(timespec='seconds')
  )


def loc(d, prefix=''):
  return (d[f'{prefix}lat'], d[f'{prefix}lng'])


def normalize_name(n):
  return re.sub(r'\W', '-', n.lower())


def get_hotspot_address(hotspot_name):
  normalized = normalize_name(hotspot_name)
  home = None
  hmap = {}
  r = requests.get('https://network.helium.com/fetchHotspots')
  for h in r.json():
    # save them by name
    stdname = normalize_name(h['name'])
    if stdname == normalized:
      home = h
    hmap[h['address']] = h
  return (home, hmap)


# TODO: redo this a bit to take some params
def main():
  hotspot_raw_name = ' '.join(sys.argv[1:])
  if len(sys.argv) > 1:
    (home, hotspot_address_map) = get_hotspot_address(' '.join(sys.argv[1:]))
  else:
    print("give your hotspot id (one-two-three) as the argument. spaces or dashes are fine.")
    sys.exit(-1)

  if not home:
    print(f"eep, we didn't find your hotspot name ({hotspot_raw_name}).")
    sys.exit(-1)

  get_activity(home, hotspot_address_map)


if __name__ == '__main__':
  main()
