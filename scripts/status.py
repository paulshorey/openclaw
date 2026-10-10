#!/usr/bin/env python3
"""Read-only native coordinator, project and map inventory."""
import argparse
import json
import subprocess
from native_coordinator import projects, verify_repository, git, connection, pilot, schedule_audit
from map_ingestion import snapshot


def github(repository, resource):
    result = subprocess.run(['gh','api','--paginate','--slurp',f'repos/{repository}/{resource}?state=open&per_page=100'],
                            capture_output=True, text=True, timeout=40)
    if result.returncode:
        return {'error': 'GitHub read failed; inspect gh authentication/network privately'}
    rows = [r for page in json.loads(result.stdout) for r in page]
    return [{key:r.get(key) for key in ('number','title','html_url','state','draft','updated_at')} for r in rows
            if resource == 'pulls' or 'pull_request' not in r]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', choices=tuple(projects()))
    parser.add_argument('--github', action='store_true', help='Also read paginated open PRs/issues')
    args = parser.parse_args()
    result = {}
    failed = False
    for slug in ([args.project] if args.project else projects()):
        try:
            item = verify_repository(slug)
            item['git_status'] = git(item['path'], 'status', '--short', '--branch')
            item['schedule'] = schedule_audit(slug)
            item['pilot'] = pilot(slug, 'status')
            db = connection(slug)
            try:
                item['active_passes'] = [dict(r) for r in db.execute("SELECT * FROM passes WHERE state='active'")]
                item['tasks'] = [dict(r) for r in db.execute('SELECT id,scope,state,thread_id,cwd,observed_status,observed_at FROM tasks')]
            finally: db.close()
            if args.github:
                for resource in ('pulls', 'issues'):
                    item[resource] = github(item['repository'], resource)
                    failed |= isinstance(item[resource], dict) and 'error' in item[resource]
            if slug == 'map': item['ingestion'] = snapshot()
            result[slug] = item
            failed |= bool(item['schedule']['drift'])
        except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
            result[slug] = {'error': str(exc)}
            failed = True
    print(json.dumps(result, indent=2))
    return int(failed)

if __name__ == '__main__':
    raise SystemExit(main())
