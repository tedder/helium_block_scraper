#!/usr/bin/env python3

# copyright 2019, MIT License.

# this script needs python3.6 or newer because of the "f-string" syntax,
# aka PEP 498's literal string interpolation. you'll also requests:
# pip3 install requests


import re
import sys
import requests
import datetime

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


activity = requests.get(f'https://explorer.helium.foundation/api/hotspots/{home["address"]}/activity')
data = activity.json().get('data')
if len(data):
  for a in reversed(data):
    reward_type = a['reward_type']
    witness_id = a['poc_witness_challenge_id']
    challenge_req_hash = a['poc_req_txn_hash']
    challenge_hash = a['poc_rx_txn_hash']

    if reward_type is not None and reward_type.startswith('poc'):
      block_id = a['reward_block_height']
      reward_amount = a['reward_amount']/100000000
      reward_time = datetime.datetime.fromtimestamp(a['reward_block_time']).isoformat()

      if reward_type == 'poc_challengers':
        print(f"{reward_time}: Block {block_id} - Mined {reward_amount} - Challenger")
      elif reward_type == 'poc_challengees':
        print(f"{reward_time}: Block {block_id} - Mined {reward_amount} - Challengee")
      elif reward_type == 'poc_witnesses':
        print(f"{reward_time}: Block {block_id} - Mined {reward_amount} - Witness")
    elif witness_id is not None:
      witness_time = datetime.datetime.fromtimestamp(a['poc_rx_txn_block_time']).isoformat()
      block_id = a['poc_rx_txn_block_height']
      print(f"{witness_time}: Block {block_id} - Challenge Witnessed {witness_id}")
    elif challenge_req_hash is not None:
      challenge_time = datetime.datetime.fromtimestamp(a['poc_req_txn_block_time']).isoformat()
      block_id = a['poc_req_txn_block_height']
      print(f"{challenge_time}: Block {block_id} - Challenge Constructed")
    elif challenge_hash is not None:
      challenge_time = datetime.datetime.fromtimestamp(a['poc_rx_txn_block_time']).isoformat()
      block_id = a['poc_rx_txn_block_height']
      challenge_id = a['poc_rx_challenge_id']
      print(f"{challenge_time}: Block {block_id} - Challenge Success {challenge_id}")
    else:
      print("Unknown")
