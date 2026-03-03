#!/usr/bin/env python3
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta

JIRA_URL = "https://toyotaresearchinstitute.atlassian.net"
EMAIL = "megan.peurach.ctr@tri.global"
API_TOKEN = "ATATT3xFfGF0r1UwSLBGBB7ZVl5EtncuNq63OmLJuXjE1ClmtITJioHfA0oIcvev9riNo2sV41j7AgOmBSixho16Co16EiWfYoQXD63OoytwpU9W4qLd0W0ziCiZeS5WHI1v7FSQFu7FyAD78SD_2IOmmPg_p0ss19kRBRZ2TYAhoPP-9CbTIVo=68EDC3BD"
RSE_BOARD_ID = 17
SPRINT_PREFIX = "RSE"

auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {"Accept": "application/json"}

# Test one specific month - let's try November 2024
print("\n=== Testing November 2024 ===\n")

month_start = datetime(2024, 11, 1)
month_end = datetime(2024, 12, 1)

print(f"Looking for sprints that ended between {month_start} and {month_end}\n")

# Get all closed sprints
url = f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/sprint"
params = {"state": "closed", "maxResults": 100}

print(f"Calling: {url}")
print(f"Params: {params}\n")

response = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)

print(f"Status Code: {response.status_code}")
print(f"Response Text: {response.text[:500]}\n")

if response.status_code != 200:
    print(f"❌ API Error: {response.status_code}")
    print(f"Response: {response.text}")
    exit(1)

try:
    data = response.json()
    all_sprints = data.get('values', [])
except Exception as e:
    print(f"❌ Error parsing JSON: {e}")
    print(f"Raw response: {response.text}")
    exit(1)

rse_sprints = [s for s in all_sprints if s.get('name', '').startswith(SPRINT_PREFIX)]

print(f"Total closed RSE sprints found: {len(rse_sprints)}\n")

# Find sprints in November
nov_sprints = []
for sprint in rse_sprints:
    end_date_str = sprint.get('endDate')
    if end_date_str:
        try:
            sprint_end = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
            if month_start <= sprint_end < month_end:
                nov_sprints.append(sprint)
                print(f"✓ Found: {sprint['name']} (ended {sprint_end.strftime('%Y-%m-%d')})")
        except Exception as e:
            print(f"Error parsing date for {sprint.get('name')}: {e}")

print(f"\nSprints in November: {len(nov_sprints)}")

# Show all closed sprints by month
print("\n=== All closed sprints by month ===")
months = {}
for sprint in rse_sprints:
    end_date_str = sprint.get('endDate')
    if end_date_str:
        try:
            sprint_end = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
            month_key = sprint_end.strftime('%Y-%m')
            if month_key not in months:
                months[month_key] = []
            months[month_key].append(sprint['name'])
        except:
            pass

for month_key in sorted(months.keys(), reverse=True)[:12]:
    print(f"  {month_key}: {', '.join(months[month_key])}")#!/usr/bin/env python3
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta

JIRA_URL = "https://toyotaresearchinstitute.atlassian.net"
EMAIL = "megan.peurach.ctr@tri.global"
API_TOKEN = "ATATT3xFfGF0r1UwSLBGBB7ZVl5EtncuNq63OmLJuXjE1ClmtITJioHfA0oIcvev9riNo2sV41j7AgOmBSixho16Co16EiWfYoQXD63OmLJuXjE1ClmtITJioHfA0oIcvev9riNo2sV41j7AgOmBSixho16Co16EiWfYoQXD63OoytwpU9W4qLd0W0ziCiZeS5WHI1v7FSQFu7FyAD78SD_2IOmmPg_p0ss19kRBRZ2TYAhoPP-9CbTIVo=68EDC3BD"
RSE_BOARD_ID = 17
SPRINT_PREFIX = "RSE"

auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {"Accept": "application/json"}

# Test one specific month - let's try November 2024
print("\n=== Testing November 2024 ===\n")

month_start = datetime(2024, 11, 1)
month_end = datetime(2024, 12, 1)

print(f"Looking for sprints that ended between {month_start} and {month_end}\n")

# Get all closed sprints
url = f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/sprint"
params = {"state": "closed", "maxResults": 100}

response = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
all_sprints = response.json().get('values', [])
rse_sprints = [s for s in all_sprints if s.get('name', '').startswith(SPRINT_PREFIX)]

print(f"Total closed RSE sprints found: {len(rse_sprints)}\n")

# Find sprints in November
nov_sprints = []
for sprint in rse_sprints:
    end_date_str = sprint.get('endDate')
    if end_date_str:
        try:
            sprint_end = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
            if month_start <= sprint_end < month_end:
                nov_sprints.append(sprint)
                print(f"✓ Found: {sprint['name']} (ended {sprint_end.strftime('%Y-%m-%d')})")
        except:
            pass

print(f"\nSprints in November: {len(nov_sprints)}")

if nov_sprints:
    print("\n=== Checking first sprint for issues ===")
    sprint = nov_sprints[0]
    sprint_id = sprint['id']
    
    # Get issues from this sprint
    url = f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue"
    params = {"maxResults": 10, "fields": "key,summary,status,resolutiondate"}
    
    response = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
    data = response.json()
    
    print(f"\nSprint: {sprint['name']}")
    print(f"Total issues in sprint: {data.get('total', 0)}")
    
    if data.get('total', 0) > 0:
        print("\nFirst 10 issues:")
        for issue in data.get('issues', [])[:10]:
            key = issue['key']
            summary = issue['fields'].get('summary', 'No summary')[:50]
            status = issue['fields'].get('status', {}).get('name', 'Unknown')
            resolution_date = issue['fields'].get('resolutiondate', 'Not resolved')
            print(f"  {key}: {summary}... | Status: {status} | Resolved: {resolution_date}")
    
    # Check for Done issues
    url = f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue"
    params = {"maxResults": 0, "fields": "key", "jql": "status = Done"}
    
    response = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
    done_count = response.json().get('total', 0)
    
    print(f"\nDone issues in this sprint: {done_count}")
else:
    print("\n❌ No sprints found in November 2024!")
    print("\nLet's check what months DO have sprints:")
    
    # Show all closed sprints by month
    months = {}
    for sprint in rse_sprints:
        end_date_str = sprint.get('endDate')
        if end_date_str:
            try:
                sprint_end = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                month_key = sprint_end.strftime('%Y-%m')
                if month_key not in months:
                    months[month_key] = []
                months[month_key].append(sprint['name'])
            except:
                pass
    
    print("\nSprints by month:")
    for month_key in sorted(months.keys()):
        print(f"  {month_key}: {', '.join(months[month_key])}")
