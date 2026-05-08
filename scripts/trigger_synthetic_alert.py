#!/usr/bin/env python3
"""
Trigger a synthetic alert by sending a test notification to Alertmanager's API.
This is intended for local demos only.

Usage:
  python3 scripts/trigger_synthetic_alert.py --alertmanager http://localhost:9093
"""
import argparse
import json
import requests

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--alertmanager', default='http://localhost:9093', help='Alertmanager base URL')
    args = parser.parse_args()

    payload = [
        {
            'labels': {'alertname': 'DemoSyntheticAlert', 'severity': 'critical'},
            'annotations': {'summary': 'Synthetic alert for demo', 'description': 'This is a test alert'},
            'startsAt': '2020-01-01T00:00:00Z'
        }
    ]

    r = requests.post(f"{args.alertmanager}/api/v1/alerts", json=payload)
    print('status', r.status_code)
    print(r.text)
