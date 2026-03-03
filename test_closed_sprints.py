#!/usr/bin/env python3
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

JIRA_URL = "https://toyotaresearchinstitute.atlassian.net"
EMAIL = "megan.peurach.ctr@tri.global"
API_TOKEN = "ATATT3xFfGF0r1UwSLBGBB7ZVl5EtncuNq63OmLJuXjE1ClmtITJioHfA0oIcvev9riNo2sV41j7AgOmBSixho16Co16EiWfYoQXD63OoytwpU9W4qLd0W0ziCiZeS5WHI1v7FSQFu7FyAD78SD_2IOmmPg_p0ss19kRBRZ2TYAhoPP-9CbTIVo=68EDC3BD"
RSE_BOARD_ID = 17
SPRINT_PREFIX = "RSE"

auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {"Accept": "application/json"}

print("\n=== Getting ALL closed RSE sprints with pagination ===\n")

all_sprints = []
start_at = 0
max_results = 50

while True:
    url = f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/sprint"
    params = {"state": "closed", "maxResults": max_results, "startAt": start_at}
    
    print(f"Fetching sprints: startAt={start_at}, maxResults={max_results}")
    
    response = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
    data = response.json()
    
    sprints = data.get('values', [])
    all_sprints.extend(sprints)
    
    print(f"  Got {len(sprints)} sprints (total so far: {len(all_sprints)})")
    
    # Check if we got all sprints
    if data.get('isLast', True):
        break
    
    start_at += max_results

print(f"\nTotal closed sprints fetched: {len(all_sprints)}")

# Filter for RSE sprints and organize by date
rse_sprints = [s for s in all_sprints if s.get('name', '').startswith(SPRINT_PREFIX)]
print(f"RSE sprints: {len(rse_sprints)}\n")

# Sort by end date
sprints_with_dates = []
for sprint in rse_sprints:
    end_date_str = sprint.get('endDate')
    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
            sprints_with_dates.append({
                'name': sprint.get('name'),
                'end_date': end_date
            })
        except:
            pass

sprints_with_dates.sort(key=lambda x: x['end_date'], reverse=True)

print("Most recent 20 RSE sprints:")
print("-" * 60)
for sprint in sprints_with_dates[:20]:
    print(f"{sprint['end_date'].strftime('%Y-%m-%d')}  |  {sprint['name']}")
