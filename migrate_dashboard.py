#!/usr/bin/env python3
"""
RSE Team Jira Dashboard Auto-Updater
Uses <!-- METRIC:key --> markers for reliable HTML updates.
Run migrate_dashboard.py once before using this script.
"""

import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime, timedelta
import re
import os
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

JIRA_URL = "https://toyotaresearchinstitute.atlassian.net"
EMAIL = "megan.peurach.ctr@tri.global"
API_TOKEN = "ATATT3xFfGF0r1UwSLBGBB7ZVl5EtncuNq63OmLJuXjE1ClmtITJioHfA0oIcvev9riNo2sV41j7AgOmBSixho16Co16EiWfYoQXD63OoytwpU9W4qLd0W0ziCiZeS5WHI1v7FSQFu7FyAD78SD_2IOmmPg_p0ss19kRBRZ2TYAhoPP-9CbTIVo=68EDC3BD"
DASHBOARD_FILE = "dashboard.html"

PROJECT_KEY = "TRI"
RSE_BOARD_ID = 17
SPRINT_PREFIX = "RSE"
RSE_TEAM_ID = "e83576e2-2517-4baf-8dd6-8d277b5eba80-3"
RSE_TEAM_NAME = "RSE"
TEAM_FIELD = "customfield_10001"

# ============================================================================
# MARKER-BASED HTML UPDATE
# ============================================================================

def set_metric(html, key, value):
    """Replace content between <!-- METRIC:key --> and <!-- /METRIC:key -->."""
    pattern = rf'(<!-- METRIC:{re.escape(key)} -->)[^<]*(<!-- /METRIC:{re.escape(key)} -->)'
    replacement = rf'\g<1>{value}\g<2>'
    new_html, n = re.subn(pattern, replacement, html)
    if n == 0:
        print(f"  ⚠ WARNING: marker not found for '{key}' — run migrate_dashboard.py first")
    return new_html

def update_html_dashboard(metrics):
    dashboard_path = Path(DASHBOARD_FILE)
    if not dashboard_path.exists():
        print(f"ERROR: {DASHBOARD_FILE} not found")
        return False

    if '<!-- METRIC:' not in dashboard_path.read_text(encoding='utf-8'):
        print("ERROR: No METRIC markers found in dashboard.html")
        print("       Please run migrate_dashboard.py first.")
        return False

    print(f"\nUpdating dashboard: {dashboard_path.absolute()}")
    html = dashboard_path.read_text(encoding='utf-8')

    # ── data-counter values (drive the animated number) ─────────────── #
    html = set_metric(html, 'sprint_total_issues',    metrics['sprint_total_issues'])
    html = set_metric(html, 'sprint_completion_rate', metrics['sprint_completion_rate'])
    html = set_metric(html, 'sprint_in_progress',     metrics['sprint_in_progress'])
    html = set_metric(html, 'sprint_to_do',           metrics['sprint_to_do'])
    html = set_metric(html, 'backlog_count',          metrics['backlog_count'])
    html = set_metric(html, 'average_velocity',       metrics['average_velocity'])
    html = set_metric(html, 'contamination_percent',  metrics['contamination_percent'])
    html = set_metric(html, 'zombie_count',           metrics['zombie_count'])

    # ── Churn breakdown counts ───────────────────────────────────────── #
    html = set_metric(html, 'done_count',        metrics['done_count'])
    html = set_metric(html, 'duplicate_count',   metrics['duplicate_count'])
    html = set_metric(html, 'not_needed_count',  metrics['not_needed_count'])
    html = set_metric(html, 'wont_do_count',     metrics['wont_do_count'])
    html = set_metric(html, 'total_resolved',    metrics['total_resolved'])

    # ── Big churn rate display ───────────────────────────────────────── #
    html = set_metric(html, 'churn_rate_display', f"{metrics['churn_rate']}%")
    html = set_metric(html, 'churned_count',      metrics['churned_count'])
    html = set_metric(html, 'total_resolved2',    metrics['total_resolved'])

    # ── Churn category labels + bars ────────────────────────────────── #
    html = set_metric(html, 'duplicate_label',   f"{metrics['duplicate_count']} ({metrics['duplicate_percent']}%)")
    html = set_metric(html, 'duplicate_bar',     f"{metrics['duplicate_percent']}%")
    html = set_metric(html, 'not_needed_label',  f"{metrics['not_needed_count']} ({metrics['not_needed_percent']}%)")
    html = set_metric(html, 'not_needed_bar',    f"{metrics['not_needed_percent']}%")
    html = set_metric(html, 'wont_do_label',     f"{metrics['wont_do_count']} ({metrics['wont_do_percent']}%)")
    html = set_metric(html, 'wont_do_bar',       f"{metrics['wont_do_percent']}%")

    # ── Completion rate display ──────────────────────────────────────── #
    html = set_metric(html, 'completion_rate_display', f"{metrics['completion_rate']}%")
    html = set_metric(html, 'done_count2',             metrics['done_count'])

    # ── Status chart data array ──────────────────────────────────────── #
    chart_data = f"{metrics['sprint_done']}, {metrics['sprint_in_review']}, {metrics['sprint_in_progress']}, {metrics['sprint_to_do']}"
    html = set_metric(html, 'status_chart_data', chart_data)

    # ── Timestamp ───────────────────────────────────────────────────── #
    now_str = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    html = set_metric(html, 'last_updated', now_str)

    dashboard_path.write_text(html, encoding='utf-8')
    print(f"✔ Dashboard updated successfully!")
    return True

# ============================================================================
# JIRA DATA FUNCTIONS  (all fixes from previous version included)
# ============================================================================

def test_jira_connection():
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    try:
        r = requests.get(f"{JIRA_URL}/rest/api/3/myself", headers=headers, auth=auth, timeout=10)
        r.raise_for_status()
        print(f"✔ Connected as: {r.json().get('displayName', 'Unknown')}")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

def is_rse_team(v):
    if not v:
        return False
    return v.get('id') == RSE_TEAM_ID or v.get('name') == RSE_TEAM_NAME

def get_active_rse_sprints():
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    try:
        r = requests.get(f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/sprint",
                         headers=headers, auth=auth, params={"state": "active"}, timeout=30)
        r.raise_for_status()
        return [s for s in r.json().get('values', []) if s.get('name', '').startswith(SPRINT_PREFIX)]
    except Exception as e:
        print(f"Error getting sprints: {e}")
        return []

def get_all_rse_sprints():
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    all_sprints = []
    for state in ["active", "closed", "future"]:
        try:
            r = requests.get(f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/sprint",
                             headers=headers, auth=auth,
                             params={"state": state, "maxResults": 100}, timeout=30)
            r.raise_for_status()
            all_sprints.extend([s for s in r.json().get('values', [])
                                 if s.get('name', '').startswith(SPRINT_PREFIX)])
        except Exception as e:
            print(f"Error getting {state} sprints: {e}")
    return all_sprints

def get_sprint_issues_paginated(sprint_id, fields=f"key,resolutiondate,resolution,status,updated,issuetype,{TEAM_FIELD}"):
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    all_issues, start_at = [], 0
    while True:
        try:
            r = requests.get(f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue",
                             headers=headers, auth=auth,
                             params={"startAt": start_at, "maxResults": 100, "fields": fields},
                             timeout=60)
            r.raise_for_status()
            data = r.json()
            issues = data.get('issues', [])
            all_issues.extend(issues)
            if len(all_issues) >= data.get('total', 0):
                break
            start_at += 100
        except Exception as e:
            print(f"    Error fetching sprint issues: {e}")
            break
    return all_issues

def get_backlog_issues(fields=None):
    if fields is None:
        fields = f"key,updated,status,resolution,resolutiondate,{TEAM_FIELD},issuetype"
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    url = f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/backlog"
    all_issues, start_at = [], 0
    print("    Fetching backlog issues...")
    while True:
        try:
            r = requests.get(url, headers=headers, auth=auth,
                             params={"startAt": start_at, "maxResults": 100, "fields": fields},
                             timeout=60)
            r.raise_for_status()
            data = r.json()
            issues = data.get('issues', [])
            all_issues.extend(issues)
            total = data.get('total', 0)
            print(f"    Fetched {len(all_issues)}/{total} backlog issues...")
            if len(all_issues) >= total:
                break
            start_at += 100
        except Exception as e:
            print(f"    Error: {e}")
            break
    return all_issues

def get_issues_in_sprint(sprint_id, jql_filter=""):
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    params = {"maxResults": 0, "fields": "summary"}
    if jql_filter:
        params["jql"] = jql_filter
    try:
        r = requests.get(f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue",
                         headers=headers, auth=auth, params=params, timeout=30)
        r.raise_for_status()
        return r.json().get('total', 0)
    except Exception as e:
        print(f"    Error: {e}")
        return 0

def get_backlog_count_via_agile_api():
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    url = f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/backlog"
    try:
        r = requests.get(url, headers=headers, auth=auth,
                         params={"maxResults": 0, "fields": "key"}, timeout=30)
        r.raise_for_status()
        total = r.json().get('total', 0)
        if total == 0:
            return 0
        all_issues, start_at = [], 0
        while len(all_issues) < total:
            r2 = requests.get(url, headers=headers, auth=auth,
                              params={"startAt": start_at, "maxResults": 100,
                                      "fields": f"status,{TEAM_FIELD}"}, timeout=30)
            r2.raise_for_status()
            data = r2.json()
            all_issues.extend(data.get('issues', []))
            if len(all_issues) >= data.get('total', 0):
                break
            start_at += 100
        return sum(1 for i in all_issues
                   if is_rse_team(i['fields'].get(TEAM_FIELD, {}))
                   and i['fields'].get('status', {}).get('name', '') != 'Done')
    except Exception as e:
        print(f"    Error: {e}")
        return 0

def get_current_sprint_stats():
    active_sprints = get_active_rse_sprints()
    if not active_sprints:
        return {'total_issues': 0, 'in_progress': 0, 'in_review': 0,
                'to_do': 0, 'done': 0, 'completion_rate': 0.0}

    sprint = active_sprints[0]
    print(f"    Fetching stats for sprint: {sprint.get('name')}")

    raw = get_sprint_issues_paginated(sprint['id'],
                                      fields=f"key,status,{TEAM_FIELD},issuetype")

    # De-duplicate and filter to RSE team
    seen, rse_issues = set(), []
    for i in raw:
        if i['key'] not in seen:
            seen.add(i['key'])
            if is_rse_team(i['fields'].get(TEAM_FIELD, {})):
                rse_issues.append(i)

    in_progress = in_review = to_do = done = 0
    for issue in rse_issues:
        status_obj  = issue['fields'].get('status', {})
        status_name = status_obj.get('name', '')
        cat_key     = status_obj.get('statusCategory', {}).get('key', '')

        if cat_key == 'done':
            done += 1
        elif 'review' in status_name.lower():
            in_review += 1
        elif cat_key == 'indeterminate':
            in_progress += 1
        elif cat_key == 'new':
            to_do += 1
        else:
            print(f"      ⚠ Unknown status '{status_name}' (cat={cat_key}) → To Do")
            to_do += 1

    total = len(rse_issues)
    rate  = round(done / total * 100, 1) if total else 0.0
    print(f"      Total: {total}, Done: {done}, In Review: {in_review}, "
          f"In Progress: {in_progress}, To Do: {to_do}")
    print(f"      Completion Rate: {rate}%")
    return {'total_issues': total, 'in_progress': in_progress,
            'in_review': in_review, 'to_do': to_do,
            'done': done, 'completion_rate': rate}

def get_average_velocity():
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    try:
        r = requests.get(f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/sprint",
                         headers=headers, auth=auth,
                         params={"state": "closed", "maxResults": 50}, timeout=30)
        r.raise_for_status()
        sprints = [s for s in r.json().get('values', [])
                   if s.get('name', '').startswith(SPRINT_PREFIX)]
        recent = sorted(sprints, key=lambda x: x.get('endDate', ''), reverse=True)[:6]
        vels   = [get_issues_in_sprint(s['id'], "status = Done") for s in recent]
        return round(sum(vels) / len(vels)) if vels else 0
    except Exception as e:
        print(f"Error: {e}")
        return 0

def get_monthly_churn():
    now            = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)
    print(f"    Looking for issues resolved since {start_of_month.strftime('%Y-%m-%d')}...")

    done_count = dup_count = not_needed_count = wont_do_count = cannot_repro_count = 0
    seen = set()

    def classify(issue_key, resolution_obj, status_obj, date_used):
        nonlocal done_count, dup_count, not_needed_count, wont_do_count, cannot_repro_count
        if issue_key in seen:
            return
        seen.add(issue_key)
        if len(seen) <= 10:
            print(f"      ✔ {issue_key} — {date_used.strftime('%Y-%m-%d')}")

        res_name = (resolution_obj.get('name', '') if resolution_obj else '') or ''
        if not res_name:
            cat = status_obj.get('statusCategory', {}).get('key', '') if status_obj else ''
            if cat == 'done':
                res_name = 'Done'

        if res_name == 'Done':
            done_count += 1
        elif res_name == 'Duplicative':
            dup_count += 1
        elif res_name in ['Not Needed', 'Not needed']:
            not_needed_count += 1
        elif res_name == "Won't Do":
            wont_do_count += 1
        elif res_name == 'Cannot Reproduce':
            cannot_repro_count += 1

    def check_issue(issue):
        issue_type = issue['fields'].get('issuetype', {}).get('name', '')
        if issue_type in ['Epic', 'Sub-task']:
            return
        if not is_rse_team(issue['fields'].get(TEAM_FIELD, {})):
            return

        resolved_str = issue['fields'].get('resolutiondate')
        if resolved_str:
            try:
                d = datetime.fromisoformat(resolved_str.replace('Z', '+00:00')).replace(tzinfo=None)
                if d >= start_of_month:
                    classify(issue['key'], issue['fields'].get('resolution'),
                             issue['fields'].get('status'), d)
                    return
            except:
                pass

        status_obj = issue['fields'].get('status', {})
        if status_obj.get('statusCategory', {}).get('key', '') == 'done':
            updated_str = issue['fields'].get('updated', '')
            if updated_str:
                try:
                    d = datetime.fromisoformat(updated_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    if d >= start_of_month:
                        classify(issue['key'], issue['fields'].get('resolution'),
                                 status_obj, d)
                except:
                    pass

    for sprint in get_all_rse_sprints():
        for issue in get_sprint_issues_paginated(sprint['id']):
            check_issue(issue)
    sprint_count = len(seen)
    print(f"    Found {sprint_count} in sprints")

    print("    Checking backlog...")
    for issue in get_backlog_issues():
        check_issue(issue)
    print(f"    Found {len(seen) - sprint_count} in backlog")
    print(f"    Total: {len(seen)} issues resolved this month")

    return {'done': done_count,
            'duplicative': dup_count + cannot_repro_count,
            'not_needed': not_needed_count,
            'wont_do': wont_do_count}

# ============================================================================
# CALCULATE + MAIN
# ============================================================================

def calculate_metrics():
    print("\nFetching RSE metrics from Jira...")
    m = {}

    print("\n  → Finding active RSE sprints...")
    active = get_active_rse_sprints()
    print(f"    Found {len(active)} active RSE sprints")
    for s in active:
        print(f"    - {s.get('name')} (ID: {s.get('id')})")

    print("\n  → Current Sprint Stats...")
    ss = get_current_sprint_stats()
    m.update({f'sprint_{k}': v for k, v in ss.items()})

    print("\n  → Current RSE Backlog...")
    m['backlog_count'] = get_backlog_count_via_agile_api()
    print(f"    Result: {m['backlog_count']} issues")

    print("\n  → Average Velocity...")
    m['average_velocity'] = get_average_velocity()
    print(f"    Result: {m['average_velocity']} points/sprint")

    print("\n  → Sprint Contamination...")
    cutoff = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    cont = total = 0
    for s in active:
        total += get_issues_in_sprint(s['id'])
        cont  += get_issues_in_sprint(s['id'], f"created < {cutoff}")
    print(f"    Old items: {cont}, Total: {total}")
    m['contamination_percent'] = round(cont / total * 100, 1) if total else 0.0

    print("\n  → Zombie Issues (90+ days not updated, backlog only)...")
    cutoff_dt = datetime.now() - timedelta(days=90)
    bl = get_backlog_issues()
    print(f"    Filtering {len(bl)} backlog issues...")
    zombies = 0
    for issue in bl:
        if not is_rse_team(issue['fields'].get(TEAM_FIELD, {})):
            continue
        if issue['fields'].get('status', {}).get('statusCategory', {}).get('key') == 'done':
            continue
        if issue['fields'].get('issuetype', {}).get('name') in ['Epic', 'Sub-task']:
            continue
        upd = issue['fields'].get('updated', '')
        if upd:
            try:
                d = datetime.fromisoformat(upd.replace('Z', '+00:00')).replace(tzinfo=None)
                if d <= cutoff_dt:
                    zombies += 1
            except:
                pass
    print(f"    Result: {zombies} issues")
    m['zombie_count'] = zombies

    print("\n  → Monthly Churn Metrics...")
    churn = get_monthly_churn()
    m['done_count']       = churn['done']
    m['duplicate_count']  = churn['duplicative']
    m['not_needed_count'] = churn['not_needed']
    m['wont_do_count']    = churn['wont_do']

    total_r  = sum(churn.values())
    churned  = churn['duplicative'] + churn['not_needed'] + churn['wont_do']
    m['total_resolved'] = total_r
    m['churned_count']  = churned

    if total_r:
        m['churn_rate']         = round(churned    / total_r * 100, 1)
        m['duplicate_percent']  = round(churn['duplicative'] / total_r * 100, 1)
        m['not_needed_percent'] = round(churn['not_needed']  / total_r * 100, 1)
        m['wont_do_percent']    = round(churn['wont_do']     / total_r * 100, 1)
        m['completion_rate']    = round(churn['done']        / total_r * 100, 1)
    else:
        m['churn_rate'] = m['duplicate_percent'] = m['not_needed_percent'] = \
        m['wont_do_percent'] = m['completion_rate'] = 0.0

    return m

def print_summary(m):
    print("\n" + "="*60)
    print("RSE TEAM DASHBOARD METRICS SUMMARY")
    print("="*60)
    print(f"\nCurrent Sprint Stats:")
    print(f"  Total Issues:           {m['sprint_total_issues']}")
    print(f"  Done:                   {m['sprint_done']}")
    print(f"  In Review:              {m['sprint_in_review']}")
    print(f"  In Progress:            {m['sprint_in_progress']}")
    print(f"  To Do:                  {m['sprint_to_do']}")
    print(f"  Completion Rate:        {m['sprint_completion_rate']}%")
    print(f"\nBacklog & Health:")
    print(f"  Current RSE Backlog:    {m['backlog_count']} issues")
    print(f"  Average Velocity:       {m['average_velocity']} points/sprint")
    print(f"  Sprint Contamination:   {m['contamination_percent']}%")
    print(f"  Zombie Issues:          {m['zombie_count']} issues")
    print(f"\nMonthly Churn:")
    print(f"  Done:                   {m['done_count']}")
    print(f"  Duplicate:              {m['duplicate_count']} ({m['duplicate_percent']}%)")
    print(f"  Not Needed:             {m['not_needed_count']} ({m['not_needed_percent']}%)")
    print(f"  Won't Do:               {m['wont_do_count']} ({m['wont_do_percent']}%)")
    print(f"  Total Churn:            {m['churned_count']} ({m['churn_rate']}%)")
    print(f"\nSuccessfully Completed:   {m['done_count']} ({m['completion_rate']}%)")
    print(f"Total Resolved:           {m['total_resolved']} issues")
    print("="*60 + "\n")

def main():
    print("\n" + "="*60)
    print("RSE TEAM JIRA DASHBOARD AUTO-UPDATER")
    print("="*60 + "\n")

    if not test_jira_connection():
        return

    try:
        metrics = calculate_metrics()
        print_summary(metrics)
        if update_html_dashboard(metrics):
            print("✔ All done!")
            print(f"✔ Last updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        else:
            print("✗ Failed to update dashboard")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
