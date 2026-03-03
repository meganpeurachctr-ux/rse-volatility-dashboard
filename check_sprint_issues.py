#!/usr/bin/env python3
import requests
from requests.auth import HTTPBasicAuth

JIRA_URL = "https://toyotaresearchinstitute.atlassian.net"
EMAIL = "megan.peurach.ctr@tri.global"
API_TOKEN = "ATATT3xFfGF0r1UwSLBGBB7ZVl5EtncuNq63OmLJuXjE1ClmtITJioHfA0oIcvev9riNo2sV41j7AgOmBSixho16Co16EiWfYoQXD63OoytwpU9W4qLd0W0ziCiZeS5WHI1v7FSQFu7FyAD78SD_2IOmmPg_p0ss19kRBRZ2TYAhoPP-9CbTIVo=68EDC3BD"
RSE_BOARD_ID = 17
TEAM_FIELD = "customfield_10001"
RSE_TEAM_ID = "e83576e2-2517-4baf-8dd6-8d277b5eba80-3"

auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {"Accept": "application/json"}

# Get active sprint
url = f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/sprint"
params = {"state": "active"}
response = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
sprints = response.json().get('values', [])
active_sprint = [s for s in sprints if s.get('name', '').startswith('RSE')][0]

print(f"\nActive Sprint: {active_sprint['name']}")
print(f"Sprint ID: {active_sprint['id']}\n")

# Get ALL issues in sprint
sprint_id = active_sprint['id']
url = f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue"
params = {"maxResults": 200, "fields": f"key,status,{TEAM_FIELD},summary"}

response = requests.get(url, headers=headers, auth=auth, params=params, timeout=60)
data = response.json()

all_issues = data.get('issues', [])
print(f"Total issues in sprint: {len(all_issues)}")

# Count by team field
with_rse_team = 0
without_team = 0
other_team = 0

status_counts = {'Done': 0, 'In Progress': 0, 'In Review': 0, 'To Do': 0}

for issue in all_issues:
    team = issue['fields'].get(TEAM_FIELD, {})
    status_name = issue['fields'].get('status', {}).get('name', 'Unknown')
    
    if team:
        if team.get('id') == RSE_TEAM_ID:
            with_rse_team += 1
            # Categorize status
            if status_name == 'Done':
                status_counts['Done'] += 1
            elif 'Review' in status_name or 'review' in status_name.lower():
                status_counts['In Review'] += 1
            elif status_name == 'In Progress':
                status_counts['In Progress'] += 1
            elif status_name in ['To Do', 'Open', 'Backlog']:
                status_counts['To Do'] += 1
        else:
            other_team += 1
            print(f"  Different team: {issue['key']} - Team: {team.get('name', 'Unknown')}")
    else:
        without_team += 1
        print(f"  No team field: {issue['key']} - {issue['fields'].get('summary', '')[:50]}")

print(f"\nBreakdown:")
print(f"  With RSE team field: {with_rse_team}")
print(f"  No team field: {without_team}")
print(f"  Other team: {other_team}")

print(f"\nRSE Team Status Breakdown:")
print(f"  Done: {status_counts['Done']}")
print(f"  In Review: {status_counts['In Review']}")
print(f"  In Progress: {status_counts['In Progress']}")
print(f"  To Do: {status_counts['To Do']}")
print(f"  Total: {sum(status_counts.values())}")

print(f"\nExpected from Jira board: 94 issues")
print(f"Script is counting: {with_rse_team} issues")
print(f"Missing: {94 - with_rse_team} issues")
