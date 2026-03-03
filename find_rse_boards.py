#!/usr/bin/env python3
import requests
from requests.auth import HTTPBasicAuth

JIRA_URL = "https://toyotaresearchinstitute.atlassian.net"
EMAIL = "megan.peurach.ctr@tri.global"
API_TOKEN = "ATATT3xFfGF0r1UwSLBGBB7ZVl5EtncuNq63OmLJuXjE1ClmtITJioHfA0oIcvev9riNo2sV41j7AgOmBSixho16Co16EiWfYoQXD63OoytwpU9W4qLd0W0ziCiZeS5WHI1v7FSQFu7FyAD78SD_2IOmmPg_p0ss19kRBRZ2TYAhoPP-9CbTIVo=68EDC3BD"

auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {"Accept": "application/json"}

print("\n=== Finding all boards with RSE sprints ===\n")

# Get all boards
url = f"{JIRA_URL}/rest/agile/1.0/board"
params = {"maxResults": 100}

response = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
boards = response.json().get('values', [])

print(f"Total boards found: {len(boards)}\n")

boards_with_rse = []

for board in boards:
    board_id = board['id']
    board_name = board['name']
    
    # Check if this board has RSE sprints
    url = f"{JIRA_URL}/rest/agile/1.0/board/{board_id}/sprint"
    params = {"state": "active", "maxResults": 10}
    
    try:
        response = requests.get(url, headers=headers, auth=auth, params=params, timeout=10)
        if response.status_code == 200:
            sprints = response.json().get('values', [])
            rse_sprints = [s for s in sprints if 'RSE' in s.get('name', '').upper()]
            
            if rse_sprints:
                boards_with_rse.append({
                    'id': board_id,
                    'name': board_name,
                    'sprints': [s['name'] for s in rse_sprints]
                })
    except:
        pass

if boards_with_rse:
    print("✓ Boards with active RSE sprints:")
    for board in boards_with_rse:
        print(f"\nBoard ID: {board['id']}")
        print(f"Board Name: {board['name']}")
        print(f"RSE Sprints: {', '.join(board['sprints'])}")
else:
    print("❌ No boards found with active RSE sprints")
    
print("\n" + "="*60)
print("Current dashboard is using Board ID: 17")
print("If the correct board is different, update RSE_BOARD_ID in your script")
print("="*60)
