#!/usr/bin/env python3

# copyright 2019, MIT License.

# this script needs python3.6 or newer because of the "f-string" syntax,
# aka PEP 498's literal string interpolation. You'll also need to install
# several required modules: pip3 install -r requirements.txt
import argparse
import re
import sys
from datetime import datetime, timezone
from time import mktime

import requests
from dateutil import parser
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


def get_activity(home, hotspot_map, since):
  hotspot_address = home['address']
  since_unix_time = mktime(since.timetuple())
  # Ideally, we could fetch just the activity afterthe `since_unix_time`
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
      if a['reward_block_time'] < since_unix_time:
        continue

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
      if a['poc_rx_txn_block_time'] < since_unix_time:
        continue

      witness_time = format_time(a['poc_rx_txn_block_time'])
      block_id = a['poc_rx_txn_block_height']
      print(f"{witness_time}: Block {block_id} - {witness_id:7} - Challenge Witnessed")
    elif challenge_req_hash is not None:
      if a['poc_req_txn_block_time'] < since_unix_time:
        continue

      challenge_time = format_time(a['poc_req_txn_block_time'])
      block_id = a['poc_req_txn_block_height']
      print(f"{challenge_time}: Block {block_id} - {id_spacing:9} Challenge Constructed")
    elif challenge_hash is not None:
      if a['poc_rx_txn_block_time'] < since_unix_time:
        continue

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


def main(hotspot, since):
  print(f"Printing activity since: {since}.")
  hotspot_raw_name = ' '.join(hotspot)
  (home, hotspot_address_map) = get_hotspot_address(hotspot_raw_name)

  if not home:
    print(f"eep, we didn't find your hotspot name ({hotspot_raw_name}).")
    return -1
  else:
    get_activity(home, hotspot_address_map, since)
  return 0


def valid_datetime_type(arg_datetime_str):
    """custom argparse type for datetime values using dateutils.parser"""
    try:
        dt = parser.parse(arg_datetime_str)
        if dt > datetime.now():
          msg = "Parsed datetime ({0}) is later than now.".format(dt)
          raise argparse.ArgumentTypeError(msg)
        else:
          return dt
    except ValueError:
        msg = "Given string ({0}) not parsable.".format(arg_datetime_str)
        raise argparse.ArgumentTypeError(msg)


if __name__ == '__main__':
  argparser = argparse.ArgumentParser()
  argparser.add_argument("--since", help="show activity after date/timestamp.",
                         required=False,
                         default=None,
                         type=valid_datetime_type
                         )
  argparser.add_argument("hotspot",
                         help=("hotspot id (one-two-three) as the argument. "
                               "spaces or dashes are fine."
                               ),
                         nargs='+'
                         )

  args = argparser.parse_args()
  sys.exit(main(args.hotspot, args.since))
