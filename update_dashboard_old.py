#!/usr/bin/env python3
"""
RSE Team Jira Dashboard Auto-Updater with Historical Data Collection
Fetches current and historical metrics from Jira for RSE team and updates both dashboards
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
HISTORICAL_DASHBOARD_FILE = "historical_dashboard.html"

PROJECT_KEY = "TRI"
RSE_BOARD_ID = 17
SPRINT_PREFIX = "RSE"
RSE_TEAM_ID = "e83576e2-2517-4baf-8dd6-8d277b5eba80-3"
RSE_TEAM_NAME = "RSE"
TEAM_FIELD = "customfield_10001"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def test_jira_connection():
    """Test the Jira connection"""
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    url = f"{JIRA_URL}/rest/api/3/myself"
    
    try:
        response = requests.get(url, headers=headers, auth=auth, timeout=10)
        response.raise_for_status()
        user_data = response.json()
        print(f"✓ Connected as: {user_data.get('displayName', 'Unknown')}")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

def is_rse_team(team_field_value):
    """Check if the team field indicates RSE team"""
    if not team_field_value:
        return False
    return team_field_value.get('id') == RSE_TEAM_ID or team_field_value.get('name') == RSE_TEAM_NAME

def get_active_rse_sprints():
    """Get all active RSE sprints"""
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    
    url = f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/sprint"
    params = {"state": "active"}
    
    try:
        response = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
        response.raise_for_status()
        sprints = response.json().get('values', [])
        return [s for s in sprints if s.get('name', '').startswith(SPRINT_PREFIX)]
    except Exception as e:
        print(f"Error getting sprints: {e}")
        return []

def get_all_rse_sprints():
    """Get ALL RSE sprints with proper pagination"""
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    
    all_sprints = []
    
    for state in ["active", "closed", "future"]:
        start_at = 0
        max_results = 50
        
        while True:
            url = f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/sprint"
            params = {"state": state, "maxResults": max_results, "startAt": start_at}
            
            try:
                response = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                sprints = data.get('values', [])
                rse_sprints = [s for s in sprints if s.get('name', '').startswith(SPRINT_PREFIX)]
                all_sprints.extend(rse_sprints)
                
                # Check if we've got all sprints
                if data.get('isLast', True):
                    break
                
                start_at += max_results
            except Exception as e:
                print(f"Error getting {state} sprints: {e}")
                break
    
    return all_sprints

def get_sprint_issues_paginated(sprint_id, fields="key,resolutiondate,resolution,issuetype,customfield_10001"):
    """Get all issues from a sprint"""
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    
    all_issues = []
    start_at = 0
    max_results = 100
    
    while True:
        url = f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue"
        params = {"startAt": start_at, "maxResults": max_results, "fields": fields}
        
        try:
            response = requests.get(url, headers=headers, auth=auth, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            issues = data.get('issues', [])
            all_issues.extend(issues)
            
            if len(all_issues) >= data.get('total', 0):
                break
            start_at += max_results
        except Exception as e:
            print(f"    Error fetching sprint issues: {e}")
            break
    
    return all_issues

def get_backlog_issues(fields="key,updated,status,resolution,customfield_10001,issuetype,created"):
    """Get backlog issues"""
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    
    all_issues = []
    start_at = 0
    max_results = 100
    
    while True:
        url = f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/backlog"
        params = {"startAt": start_at, "maxResults": max_results, "fields": fields}
        
        try:
            response = requests.get(url, headers=headers, auth=auth, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            issues = data.get('issues', [])
            all_issues.extend(issues)
            
            if len(all_issues) >= data.get('total', 0):
                break
            start_at += max_results
        except Exception as e:
            print(f"    Error: {e}")
            break
    
    return all_issues

def get_issues_in_sprint(sprint_id, jql_filter=""):
    """Get count of issues in a sprint"""
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    
    url = f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue"
    params = {"maxResults": 0, "fields": "summary"}
    
    if jql_filter:
        params["jql"] = jql_filter
    
    try:
        response = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
        response.raise_for_status()
        return response.json().get('total', 0)
    except Exception as e:
        print(f"    Error: {e}")
        return 0

def get_backlog_count_via_agile_api():
    """Get RSE backlog count using Agile API board endpoint"""
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    
    url = f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/backlog"
    params = {"maxResults": 0, "fields": "key"}
    
    try:
        response = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        total = data.get('total', 0)
        
        if total > 0:
            all_issues = []
            start_at = 0
            max_results = 100
            
            while len(all_issues) < total:
                params = {"startAt": start_at, "maxResults": max_results, "fields": f"status,{TEAM_FIELD}"}
                response = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                issues = data.get('issues', [])
                all_issues.extend(issues)
                
                if len(all_issues) >= data.get('total', 0):
                    break
                start_at += max_results
            
            count = 0
            for issue in all_issues:
                team = issue['fields'].get(TEAM_FIELD, {})
                status = issue['fields'].get('status', {}).get('name', '')
                if is_rse_team(team) and status != 'Done':
                    count += 1
            return count
        return 0
    except Exception as e:
        print(f"    Error: {e}")
        return 0

def get_current_sprint_stats():
    """Get current sprint statistics - all issues in RSE sprint"""
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    
    active_sprints = get_active_rse_sprints()
    
    if not active_sprints:
        return {
            'total_issues': 0,
            'in_progress': 0,
            'in_review': 0,
            'to_do': 0,
            'done': 0,
            'completion_rate': 0.0
        }
    
    sprint = active_sprints[0]
    sprint_id = sprint['id']
    
    print(f"    Fetching stats for sprint: {sprint.get('name')}")
    
    sprint_issues = get_sprint_issues_paginated(
        sprint_id,
        fields="key,status,customfield_10001,issuetype"
    )
    
    # Count ALL issues in RSE sprint, not just RSE team
    all_issues = sprint_issues
    
    total_issues = len(all_issues)
    in_progress = 0
    in_review = 0
    to_do = 0
    done = 0
    
    for issue in all_issues:
        status_name = issue['fields'].get('status', {}).get('name', '')
        status_category = issue['fields'].get('status', {}).get('statusCategory', {}).get('key', '')
        
        if status_category == 'done' or status_name == 'Done':
            done += 1
        elif status_name == 'In Review' or 'review' in status_name.lower():
            in_review += 1
        elif status_name == 'In Progress' or status_category == 'indeterminate':
            in_progress += 1
        elif status_name in ['To Do', 'Open', 'Backlog'] or status_category == 'new':
            to_do += 1
        else:
            in_progress += 1
    
    completion_rate = round((done / total_issues * 100), 1) if total_issues > 0 else 0.0
    
    print(f"      Total: {total_issues}, Done: {done}, In Review: {in_review}, In Progress: {in_progress}, To Do: {to_do}")
    print(f"      Completion Rate: {completion_rate}%")
    
    return {
        'total_issues': total_issues,
        'in_progress': in_progress,
        'in_review': in_review,
        'to_do': to_do,
        'done': done,
        'completion_rate': completion_rate
    }

def get_average_velocity():
    """Calculate average velocity from last 6 sprints"""
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    
    url = f"{JIRA_URL}/rest/agile/1.0/board/{RSE_BOARD_ID}/sprint"
    params = {"state": "closed", "maxResults": 50}
    
    try:
        response = requests.get(url, headers=headers, auth=auth, params=params, timeout=30)
        response.raise_for_status()
        sprints = response.json().get('values', [])
        rse_sprints = [s for s in sprints if s.get('name', '').startswith(SPRINT_PREFIX)]
        
        recent_sprints = sorted(rse_sprints, key=lambda x: x.get('endDate', ''), reverse=True)[:6]
        
        velocities = []
        for sprint in recent_sprints:
            completed_count = get_issues_in_sprint(sprint['id'], "status = Done")
            velocities.append(completed_count)
        
        if velocities:
            return round(sum(velocities) / len(velocities))
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 0

def get_monthly_churn():
    """Get monthly churn metrics using resolutiondate field"""
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)
    return get_monthly_churn_for_period(start_of_month, now)

def get_monthly_churn_for_period(start_date, end_date):
    """Get monthly churn metrics for a specific time period"""
    auth = HTTPBasicAuth(EMAIL, API_TOKEN)
    headers = {"Accept": "application/json"}
    
    done_count = 0
    duplicative_count = 0
    not_needed_count = 0
    wont_do_count = 0
    cannot_reproduce_count = 0
    seen_resolved = set()
    
    # Check all sprints
    all_sprints = get_all_rse_sprints()
    
    for sprint in all_sprints:
        sprint_issues = get_sprint_issues_paginated(sprint['id'])
        
        for issue in sprint_issues:
            issue_key = issue['key']
            if issue_key in seen_resolved:
                continue
            
            team = issue['fields'].get(TEAM_FIELD, {})
            if not is_rse_team(team):
                continue
            
            issue_type = issue['fields'].get('issuetype', {}).get('name', '')
            if issue_type in ['Epic', 'Sub-task']:
                continue
            
            resolution = issue['fields'].get('resolution')
            if not resolution:
                continue
            
            resolved_str = issue['fields'].get('resolutiondate')
            if not resolved_str:
                continue
            
            try:
                resolved_date = datetime.fromisoformat(resolved_str.replace('Z', '+00:00'))
                resolved_date = resolved_date.replace(tzinfo=None)
                
                if start_date <= resolved_date < end_date:
                    resolution_name = resolution.get('name', '')
                    seen_resolved.add(issue_key)
                    
                    if resolution_name == 'Done':
                        done_count += 1
                    elif resolution_name == 'Duplicative':
                        duplicative_count += 1
                    elif resolution_name in ['Not Needed', 'Not needed']:
                        not_needed_count += 1
                    elif resolution_name == "Won't Do":
                        wont_do_count += 1
                    elif resolution_name == 'Cannot Reproduce':
                        cannot_reproduce_count += 1
            except:
                pass
    
    # Also check backlog
    backlog_issues = get_backlog_issues(fields="key,resolutiondate,resolution,issuetype,customfield_10001")
    
    for issue in backlog_issues:
        issue_key = issue['key']
        
        if issue_key in seen_resolved:
            continue
        
        team = issue['fields'].get(TEAM_FIELD, {})
        if not is_rse_team(team):
            continue
        
        issue_type = issue['fields'].get('issuetype', {}).get('name', '')
        if issue_type in ['Epic', 'Sub-task']:
            continue
        
        resolution = issue['fields'].get('resolution')
        if not resolution:
            continue
        
        resolved_str = issue['fields'].get('resolutiondate')
        if not resolved_str:
            continue
        
        try:
            resolved_date = datetime.fromisoformat(resolved_str.replace('Z', '+00:00'))
            resolved_date = resolved_date.replace(tzinfo=None)
            
            if start_date <= resolved_date < end_date:
                resolution_name = resolution.get('name', '')
                seen_resolved.add(issue_key)
                
                if resolution_name == 'Done':
                    done_count += 1
                elif resolution_name == 'Duplicative':
                    duplicative_count += 1
                elif resolution_name in ['Not Needed', 'Not needed']:
                    not_needed_count += 1
                elif resolution_name == "Won't Do":
                    wont_do_count += 1
                elif resolution_name == 'Cannot Reproduce':
                    cannot_reproduce_count += 1
        except:
            pass
    
    return {
        'done': done_count,
        'duplicative': duplicative_count + cannot_reproduce_count,
        'not_needed': not_needed_count,
        'wont_do': wont_do_count
    }

def calculate_metrics():
    """Calculate all current metrics"""
    print("\nFetching RSE metrics from Jira...")
    print(f"Using Board ID: {RSE_BOARD_ID}")
    
    metrics = {}
    
    print("\n  → Finding active RSE sprints...")
    active_sprints = get_active_rse_sprints()
    print(f"    Found {len(active_sprints)} active RSE sprints")
    for sprint in active_sprints:
        print(f"    - {sprint.get('name')} (ID: {sprint.get('id')})")
    
    print("\n  → Current Sprint Stats...")
    sprint_stats = get_current_sprint_stats()
    metrics['sprint_total_issues'] = sprint_stats['total_issues']
    metrics['sprint_in_progress'] = sprint_stats['in_progress']
    metrics['sprint_in_review'] = sprint_stats['in_review']
    metrics['sprint_to_do'] = sprint_stats['to_do']
    metrics['sprint_done'] = sprint_stats['done']
    metrics['sprint_completion_rate'] = sprint_stats['completion_rate']
    
    print("\n  → Current RSE Backlog...")
    metrics['backlog_count'] = get_backlog_count_via_agile_api()
    print(f"    Result: {metrics['backlog_count']} issues")
    
    print("\n  → Average Velocity...")
    metrics['average_velocity'] = get_average_velocity()
    print(f"    Result: {metrics['average_velocity']} points/sprint")
    
    print("\n  → Sprint Contamination...")
    cutoff_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    contamination_count = 0
    current_sprint_count = 0
    for sprint in active_sprints:
        total = get_issues_in_sprint(sprint['id'])
        old_items = get_issues_in_sprint(sprint['id'], f"created < {cutoff_date}")
        contamination_count += old_items
        current_sprint_count += total
    
    print(f"    Old items: {contamination_count}, Total: {current_sprint_count}")
    metrics['contamination_percent'] = round((contamination_count / current_sprint_count) * 100, 1) if current_sprint_count > 0 else 0.0
    
    print("\n  → Zombie Issues (90+ days not updated, in backlog only)...")
    ninety_days_ago = datetime.now() - timedelta(days=90)
    backlog_issues = get_backlog_issues()
    print(f"    Filtering {len(backlog_issues)} backlog issues...")
    
    zombie_count = 0
    for issue in backlog_issues:
        team = issue['fields'].get(TEAM_FIELD, {})
        if not is_rse_team(team):
            continue
        
        status = issue['fields'].get('status', {}).get('statusCategory', {}).get('key', '')
        issue_type = issue['fields'].get('issuetype', {}).get('name', '')
        updated_str = issue['fields'].get('updated', '')
        
        if status != 'done' and issue_type not in ['Epic', 'Sub-task'] and updated_str:
            try:
                updated_date = datetime.fromisoformat(updated_str.replace('Z', '+00:00')).replace(tzinfo=None)
                if updated_date <= ninety_days_ago:
                    zombie_count += 1
            except:
                pass
    
    print(f"    Result: {zombie_count} issues")
    metrics['zombie_count'] = zombie_count
    
    print("\n  → Monthly Churn Metrics...")
    churn_data = get_monthly_churn()
    
    metrics['done_count'] = churn_data['done']
    metrics['duplicate_count'] = churn_data['duplicative']
    metrics['not_needed_count'] = churn_data['not_needed']
    metrics['wont_do_count'] = churn_data['wont_do']
    
    total_resolved = sum(churn_data.values())
    churned = churn_data['duplicative'] + churn_data['not_needed'] + churn_data['wont_do']
    
    metrics['total_resolved'] = total_resolved
    metrics['churned_count'] = churned
    
    if total_resolved > 0:
        metrics['churn_rate'] = round((churned / total_resolved) * 100, 1)
        metrics['duplicate_percent'] = round((churn_data['duplicative'] / total_resolved) * 100, 1)
        metrics['not_needed_percent'] = round((churn_data['not_needed'] / total_resolved) * 100, 1)
        metrics['wont_do_percent'] = round((churn_data['wont_do'] / total_resolved) * 100, 1)
        metrics['completion_rate'] = round((churn_data['done'] / total_resolved) * 100, 1)
    else:
        metrics['churn_rate'] = 0.0
        metrics['duplicate_percent'] = 0.0
        metrics['not_needed_percent'] = 0.0
        metrics['wont_do_percent'] = 0.0
        metrics['completion_rate'] = 0.0
    
    return metrics

def calculate_historical_metrics():
    """Calculate 6 months of historical metrics"""
    print("\n" + "="*60)
    print("COLLECTING 6-MONTH HISTORICAL DATA")
    print("="*60)
    
    now = datetime.now()
    historical_data = {
        'months': [],
        'churn': [],
        'contamination': [],
        'velocity': [],
        'zombies': []
    }
    
    # Calculate for last 6 months
    for i in range(5, -1, -1):
        # Calculate month start/end
        if i == 0:
            month_start = datetime(now.year, now.month, 1)
            month_end = now
        else:
            target_date = now - timedelta(days=30 * i)
            month_start = datetime(target_date.year, target_date.month, 1)
            
            # Calculate end of month
            if target_date.month == 12:
                month_end = datetime(target_date.year + 1, 1, 1)
            else:
                month_end = datetime(target_date.year, target_date.month + 1, 1)
        
        month_label = month_start.strftime('%b %y')
        historical_data['months'].append(month_label)
        
        print(f"\n→ Processing {month_label} ({month_start.strftime('%Y-%m-%d')} to {month_end.strftime('%Y-%m-%d')})")
        
        # 1. Churn Rate for this month
        print(f"  • Calculating churn rate...")
        churn_data = get_monthly_churn_for_period(month_start, month_end)
        total_resolved = sum(churn_data.values())
        churned = churn_data['duplicative'] + churn_data['not_needed'] + churn_data['wont_do']
        
        if total_resolved > 0:
            churn_rate = round((churned / total_resolved) * 100, 1)
        else:
            churn_rate = 0.0
        
        historical_data['churn'].append(churn_rate)
        print(f"    Result: {churn_rate}% ({churned}/{total_resolved} resolved)")
        
        # 2. Sprint Contamination - get sprints that ended in this month
        print(f"  • Calculating contamination...")
        all_sprints = get_all_rse_sprints()
        month_sprints = []
        
        for sprint in all_sprints:
            end_date_str = sprint.get('endDate')
            if end_date_str:
                try:
                    sprint_end = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    if month_start <= sprint_end < month_end:
                        month_sprints.append(sprint)
                except:
                    pass
        
        if month_sprints:
            total_contamination = 0
            total_issues = 0
            
            for sprint in month_sprints:
                sprint_start_str = sprint.get('startDate')
                if not sprint_start_str:
                    continue
                
                try:
                    sprint_start = datetime.fromisoformat(sprint_start_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    cutoff_date = sprint_start - timedelta(days=14)
                    cutoff_str = cutoff_date.strftime('%Y-%m-%d')
                    
                    total = get_issues_in_sprint(sprint['id'])
                    old_items = get_issues_in_sprint(sprint['id'], f"created < {cutoff_str}")
                    
                    total_contamination += old_items
                    total_issues += total
                except:
                    pass
            
            if total_issues > 0:
                contamination_rate = round((total_contamination / total_issues) * 100, 1)
            else:
                contamination_rate = 0.0
        else:
            contamination_rate = 0.0
        
        historical_data['contamination'].append(contamination_rate)
        print(f"    Result: {contamination_rate}% ({len(month_sprints)} sprints)")
        
        # 3. Velocity - average for sprints completed in this month
        print(f"  • Calculating velocity...")
        if month_sprints:
            velocities = []
            for sprint in month_sprints:
                completed_count = get_issues_in_sprint(sprint['id'], "status = Done")
                velocities.append(completed_count)
            
            avg_velocity = round(sum(velocities) / len(velocities)) if velocities else 0
        else:
            avg_velocity = 0
        
        historical_data['velocity'].append(avg_velocity)
        print(f"    Result: {avg_velocity} points")
        
        # 4. Zombie count at end of month (snapshot)
        print(f"  • Calculating zombie count...")
        ninety_days_before_month_end = month_end - timedelta(days=90)
        
        # Get backlog snapshot (approximate - issues that existed at month_end)
        backlog_issues = get_backlog_issues()
        zombie_count = 0
        
        for issue in backlog_issues:
            team = issue['fields'].get(TEAM_FIELD, {})
            if not is_rse_team(team):
                continue
            
            status = issue['fields'].get('status', {}).get('statusCategory', {}).get('key', '')
            issue_type = issue['fields'].get('issuetype', {}).get('name', '')
            updated_str = issue['fields'].get('updated', '')
            created_str = issue['fields'].get('created', '')
            
            if status != 'done' and issue_type not in ['Epic', 'Sub-task'] and updated_str and created_str:
                try:
                    updated_date = datetime.fromisoformat(updated_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    created_date = datetime.fromisoformat(created_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    
                    # Issue existed before month_end and was last updated before 90 days before month_end
                    if created_date < month_end and updated_date <= ninety_days_before_month_end:
                        zombie_count += 1
                except:
                    pass
        
        historical_data['zombies'].append(zombie_count)
        print(f"    Result: {zombie_count} zombies")
    
    print("\n" + "="*60)
    return historical_data

def update_html_dashboard(metrics):
    """Update the HTML dashboard"""
    dashboard_path = Path(DASHBOARD_FILE)
    
    if not dashboard_path.exists():
        print(f"ERROR: Dashboard file not found: {DASHBOARD_FILE}")
        return False
    
    print(f"\nUpdating dashboard: {dashboard_path.absolute()}")
    
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Update Summary Stats (top 4 cards)
    html = re.sub(
        r'(<div class="text-3xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent" data-counter=")\d+(")',
        lambda m: f'{m.group(1)}{metrics["sprint_total_issues"]}{m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<div class="text-3xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent" data-counter=")\d+(" data-decimal="true">)',
        lambda m: f'{m.group(1)}{metrics["sprint_completion_rate"]}{m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<div class="text-3xl font-bold bg-gradient-to-r from-orange-600 to-amber-600 bg-clip-text text-transparent" data-counter=")\d+(")',
        lambda m: f'{m.group(1)}{metrics["sprint_in_progress"]}{m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<div class="text-3xl font-bold bg-gradient-to-r from-purple-600 to-violet-600 bg-clip-text text-transparent" data-counter=")\d+(")',
        lambda m: f'{m.group(1)}{metrics["sprint_to_do"]}{m.group(2)}',
        html, count=1
    )
    
    # Update main metric cards
    html = re.sub(
        r'(<div class="text-4xl font-bold bg-gradient-to-r from-blue-600 to-blue-800 bg-clip-text text-transparent mb-1" data-counter=")\d+(")',
        lambda m: f'{m.group(1)}{metrics["backlog_count"]}{m.group(2)}',
        html
    )
    
    html = re.sub(
        r'(<div class="text-4xl font-bold bg-gradient-to-r from-green-600 to-emerald-800 bg-clip-text text-transparent mb-1" data-counter=")\d+(")',
        lambda m: f'{m.group(1)}{metrics["average_velocity"]}{m.group(2)}',
        html
    )
    
    html = re.sub(
        r'(<div class="text-4xl font-bold bg-gradient-to-r from-orange-600 to-amber-800 bg-clip-text text-transparent mb-1" data-counter=")[\d.]+(" data-decimal="true">)',
        lambda m: f'{m.group(1)}{metrics["contamination_percent"]}{m.group(2)}',
        html
    )
    
    html = re.sub(
        r'(<div class="text-4xl font-bold bg-gradient-to-r from-purple-600 to-violet-800 bg-clip-text text-transparent mb-1" data-counter=")\d+(")',
        lambda m: f'{m.group(1)}{metrics["zombie_count"]}{m.group(2)}',
        html
    )
    
    # Update churn metrics
    html = re.sub(
        r'(<span class="text-2xl font-bold text-green-600">)\d+(</span>)',
        lambda m: f'{m.group(1)}{metrics["done_count"]}{m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<span class="text-2xl font-bold text-blue-600">)\d+(</span>)',
        lambda m: f'{m.group(1)}{metrics["duplicate_count"]}{m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<span class="text-2xl font-bold text-amber-600">)\d+(</span>)',
        lambda m: f'{m.group(1)}{metrics["not_needed_count"]}{m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<span class="text-2xl font-bold text-red-600">)\d+(</span>)',
        lambda m: f'{m.group(1)}{metrics["wont_do_count"]}{m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<span class="text-2xl font-bold text-slate-800">)\d+(</span>)',
        lambda m: f'{m.group(1)}{metrics["total_resolved"]}{m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<div class="text-5xl font-bold bg-gradient-to-r from-red-600 to-orange-600 bg-clip-text text-transparent mb-2">)[\d.]+%(</div>\s*<div class="text-xs text-slate-600">)\d+( churned items out of )\d+( total)',
        lambda m: f'{m.group(1)}{metrics["churn_rate"]}%{m.group(2)}{metrics["churned_count"]}{m.group(3)}{metrics["total_resolved"]}{m.group(4)}',
        html
    )
    
    html = re.sub(
        r'(<span class="font-semibold text-blue-600">)\d+ \([\d.]+%\)(</span>)',
        lambda m: f'{m.group(1)}{metrics["duplicate_count"]} ({metrics["duplicate_percent"]}%){m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<div class="bg-blue-500 h-1\.5 rounded-full progress-bar" style="width: )[\d.]+%(;">)',
        lambda m: f'{m.group(1)}{metrics["duplicate_percent"]}%{m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<span class="font-semibold text-amber-600">)\d+ \([\d.]+%\)(</span>)',
        lambda m: f'{m.group(1)}{metrics["not_needed_count"]} ({metrics["not_needed_percent"]}%){m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<div class="bg-amber-500 h-1\.5 rounded-full progress-bar" style="width: )[\d.]+%(;">)',
        lambda m: f'{m.group(1)}{metrics["not_needed_percent"]}%{m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<span class="font-semibold text-red-600">)\d+ \([\d.]+%\)(</span>)',
        lambda m: f'{m.group(1)}{metrics["wont_do_count"]} ({metrics["wont_do_percent"]}%){m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<div class="bg-red-500 h-1\.5 rounded-full progress-bar" style="width: )[\d.]+%(;">)',
        lambda m: f'{m.group(1)}{metrics["wont_do_percent"]}%{m.group(2)}',
        html, count=1
    )
    
    html = re.sub(
        r'(<div class="text-4xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">)[\d.]+%(</div>\s*<div class="text-xs text-slate-600 mt-1">)\d+( successfully completed)',
        lambda m: f'{m.group(1)}{metrics["completion_rate"]}%{m.group(2)}{metrics["done_count"]}{m.group(3)}',
        html
    )
    
    # Update Status Chart data
    html = re.sub(
        r"(labels: \[)'Done', 'In Review', 'In Progress', 'To Do'(\],\s+datasets: \[\{\s+data: \[)\d+, \d+, \d+, \d+",
        lambda m: f"{m.group(1)}'Done', 'In Review', 'In Progress', 'To Do'{m.group(2)}{metrics['sprint_done']}, {metrics['sprint_in_review']}, {metrics['sprint_in_progress']}, {metrics['sprint_to_do']}",
        html
    )
    
    # Update timestamp
    now = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    html = re.sub(
        r'(<span id="lastUpdated">)[^<]*(</span>)',
        lambda m: f'{m.group(1)}{now}{m.group(2)}',
        html
    )
    
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ Dashboard updated successfully!")
    return True

def update_historical_dashboard(historical_data):
    """Update the historical trends dashboard"""
    dashboard_path = Path(HISTORICAL_DASHBOARD_FILE)
    
    if not dashboard_path.exists():
        print(f"WARNING: Historical dashboard not found: {HISTORICAL_DASHBOARD_FILE}")
        print("Skipping historical dashboard update.")
        return False
    
    print(f"\nUpdating historical dashboard: {dashboard_path.absolute()}")
    
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Update month labels
    months_js = json.dumps(historical_data['months'])
    html = re.sub(
        r'(var historicalMonths = )\[.*?\];',
        f'\\1{months_js};',
        html
    )
    
    # Update churn data
    churn_js = json.dumps(historical_data['churn'])
    html = re.sub(
        r'(var historicalChurnData = )\[.*?\];',
        f'\\1{churn_js};',
        html
    )
    
    # Update contamination data
    contamination_js = json.dumps(historical_data['contamination'])
    html = re.sub(
        r'(var historicalContaminationData = )\[.*?\];',
        f'\\1{contamination_js};',
        html
    )
    
    # Update velocity data
    velocity_js = json.dumps(historical_data['velocity'])
    html = re.sub(
        r'(var historicalVelocityData = )\[.*?\];',
        f'\\1{velocity_js};',
        html
    )
    
    # Update zombie data
    zombies_js = json.dumps(historical_data['zombies'])
    html = re.sub(
        r'(var historicalZombieData = )\[.*?\];',
        f'\\1{zombies_js};',
        html
    )
    
    # Update timestamp
    now = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    html = re.sub(
        r'(<span id="lastUpdated">)[^<]*(</span>)',
        lambda m: f'{m.group(1)}{now}{m.group(2)}',
        html
    )
    
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ Historical dashboard updated successfully!")
    return True

def print_summary(metrics):
    """Print summary"""
    print("\n" + "="*60)
    print("RSE TEAM DASHBOARD METRICS SUMMARY")
    print("="*60)
    print(f"\nCurrent Sprint Stats:")
    print(f"  Total Issues:           {metrics['sprint_total_issues']}")
    print(f"  Done:                   {metrics['sprint_done']}")
    print(f"  In Review:              {metrics['sprint_in_review']}")
    print(f"  In Progress:            {metrics['sprint_in_progress']}")
    print(f"  To Do:                  {metrics['sprint_to_do']}")
    print(f"  Completion Rate:        {metrics['sprint_completion_rate']}%")
    print(f"\nBacklog & Health:")
    print(f"  Current RSE Backlog:    {metrics['backlog_count']} issues")
    print(f"  Average Velocity:       {metrics['average_velocity']} points/sprint")
    print(f"  Sprint Contamination:   {metrics['contamination_percent']}%")
    print(f"  Zombie Issues:          {metrics['zombie_count']} issues")
    print(f"\nMonthly Churn Breakdown:")
    print(f"  Duplicate:              {metrics['duplicate_count']} ({metrics['duplicate_percent']}%)")
    print(f"  Not Needed:             {metrics['not_needed_count']} ({metrics['not_needed_percent']}%)")
    print(f"  Won't Do:               {metrics['wont_do_count']} ({metrics['wont_do_percent']}%)")
    print(f"  Total Churn:            {metrics['churned_count']} ({metrics['churn_rate']}%)")
    print(f"\nSuccessfully Completed:   {metrics['done_count']} ({metrics['completion_rate']}%)")
    print(f"Total Resolved:           {metrics['total_resolved']} issues")
    print("="*60 + "\n")

def main():
    """Main function"""
    print("\n" + "="*60)
    print("RSE TEAM JIRA DASHBOARD AUTO-UPDATER")
    print("="*60 + "\n")
    
    if not test_jira_connection():
        return
    
    try:
        # Calculate current metrics
        metrics = calculate_metrics()
        print_summary(metrics)
        
        # Update main dashboard
        success = update_html_dashboard(metrics)
        
        if success:
            print("✓ Main dashboard updated!")
        else:
            print("✗ Failed to update main dashboard")
        
        # Calculate and update historical data
        print("\n" + "="*60)
        print("UPDATING HISTORICAL TRENDS DASHBOARD")
        print("="*60)
        
        historical_data = calculate_historical_metrics()
        
        # Print historical summary
        print("\n" + "="*60)
        print("HISTORICAL DATA SUMMARY")
        print("="*60)
        print(f"Months: {', '.join(historical_data['months'])}")
        print(f"Churn Rates: {historical_data['churn']}")
        print(f"Contamination: {historical_data['contamination']}")
        print(f"Velocities: {historical_data['velocity']}")
        print(f"Zombies: {historical_data['zombies']}")
        print("="*60 + "\n")
        
        historical_success = update_historical_dashboard(historical_data)
        
        if historical_success:
            print("✓ Historical dashboard updated!")
        
        if success and historical_success:
            print("\n" + "="*60)
            print("✓ ALL DASHBOARDS UPDATED SUCCESSFULLY!")
            print(f"✓ Last updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
            print("="*60)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()