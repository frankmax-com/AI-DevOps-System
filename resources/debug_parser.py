#!/usr/bin/env python3
import sys
from pathlib import Path

# Add the resources directory to the path
sys.path.insert(0, 'resources')

# Import the parser
exec(open('resources/project-management-rebuild.py').read())

# Test the parser
parser = SpecificationParser(Path('.specs'))
tasks = parser.parse_tasks()

print("Found phases:")
for phase in tasks['phases']:
    print(f"  Phase {phase['phase']}: {phase['title']}")

print(f"\nTotal phases: {tasks['total_phases']}")
print(f"Total tasks: {tasks['total_tasks']}")
