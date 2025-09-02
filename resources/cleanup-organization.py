#!/usr/bin/env python3
"""
GitHub Organization Cleanup Script
==================================

This script completely cleans the AI-DevOps-Org-2025 organization,
removing all projects, issues, repositories, and resetting it to a
fresh state ready for the new project management rebuild.

WARNING: This script will DELETE ALL DATA in the organization.
Make sure you have backups before running this script.

Usage:
    python cleanup-organization.py --confirm-deletion
    python cleanup-organization.py --dry-run  # Preview what will be deleted
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('organization-cleanup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GitHubOrganizationCleaner:
    """Cleans GitHub organization completely"""
    
    def __init__(self, org_name: str, dry_run: bool = False):
        self.org_name = org_name
        self.dry_run = dry_run
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Statistics
        self.stats = {
            'projects_deleted': 0,
            'repositories_deleted': 0,
            'issues_deleted': 0,
            'teams_cleaned': 0,
            'errors': 0
        }
    
    def validate_prerequisites(self) -> bool:
        """Validate GitHub CLI and authentication"""
        try:
            # Check GitHub CLI
            result = subprocess.run(['gh', '--version'], 
                                  capture_output=True, text=True, check=False)
            if result.returncode != 0:
                self.logger.error("GitHub CLI not found. Install from https://cli.github.com/")
                return False
            
            # Check authentication
            result = subprocess.run(['gh', 'auth', 'status'], 
                                  capture_output=True, text=True, check=False)
            if result.returncode != 0:
                self.logger.error("GitHub CLI not authenticated. Run: gh auth login")
                return False
            
            # Check organization access
            result = subprocess.run([
                'gh', 'api', f'/orgs/{self.org_name}'
            ], capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                self.logger.error(f"Cannot access organization {self.org_name}")
                return False
            
            self.logger.info("Prerequisites validated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Prerequisites validation failed: {e}")
            return False
    
    def get_organization_inventory(self) -> Dict[str, List]:
        """Get complete inventory of organization resources"""
        try:
            inventory = {
                'projects': [],
                'repositories': [],
                'teams': [],
                'issues': []
            }
            
            # Get projects
            self.logger.info("Scanning organization projects...")
            result = subprocess.run([
                'gh', 'project', 'list', '--owner', self.org_name, '--format', 'json'
            ], capture_output=True, text=True, check=False)
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    projects_data = json.loads(result.stdout)
                    inventory['projects'] = projects_data.get('projects', [])
                except json.JSONDecodeError:
                    self.logger.warning("Could not parse projects JSON")
            
            # Get repositories
            self.logger.info("Scanning organization repositories...")
            result = subprocess.run([
                'gh', 'repo', 'list', self.org_name, '--json', 'name,url,isPrivate'
            ], capture_output=True, text=True, check=False)
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    inventory['repositories'] = json.loads(result.stdout)
                except json.JSONDecodeError:
                    self.logger.warning("Could not parse repositories JSON")
            
            # Get teams
            self.logger.info("Scanning organization teams...")
            result = subprocess.run([
                'gh', 'api', f'/orgs/{self.org_name}/teams'
            ], capture_output=True, text=True, check=False)
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    inventory['teams'] = json.loads(result.stdout)
                except json.JSONDecodeError:
                    self.logger.warning("Could not parse teams JSON")
            
            # Get issues across all repositories
            self.logger.info("Scanning issues across repositories...")
            for repo in inventory['repositories']:
                repo_name = repo['name']
                result = subprocess.run([
                    'gh', 'issue', 'list', '--repo', f"{self.org_name}/{repo_name}",
                    '--state', 'all', '--json', 'number,title,state'
                ], capture_output=True, text=True, check=False)
                
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        repo_issues = json.loads(result.stdout)
                        for issue in repo_issues:
                            issue['repository'] = repo_name
                        inventory['issues'].extend(repo_issues)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Could not parse issues for {repo_name}")
            
            # Log inventory summary
            self.logger.info(f"Organization inventory:")
            self.logger.info(f"  Projects: {len(inventory['projects'])}")
            self.logger.info(f"  Repositories: {len(inventory['repositories'])}")
            self.logger.info(f"  Teams: {len(inventory['teams'])}")
            self.logger.info(f"  Issues: {len(inventory['issues'])}")
            
            return inventory
            
        except Exception as e:
            self.logger.error(f"Failed to get organization inventory: {e}")
            return {'projects': [], 'repositories': [], 'teams': [], 'issues': []}
    
    def delete_projects(self, projects: List[Dict]) -> bool:
        """Delete all GitHub projects"""
        try:
            if not projects:
                self.logger.info("No projects to delete")
                return True
            
            self.logger.info(f"Deleting {len(projects)} projects...")
            
            for project in projects:
                project_id = project.get('id') or project.get('number')
                project_title = project.get('title', 'Unknown')
                
                if not project_id:
                    self.logger.warning(f"No ID found for project: {project_title}")
                    continue
                
                if self.dry_run:
                    self.logger.info(f"[DRY RUN] Would delete project: {project_title} (ID: {project_id})")
                    self.stats['projects_deleted'] += 1
                    continue
                
                try:
                    result = subprocess.run([
                        'gh', 'project', 'delete', str(project_id), '--owner', self.org_name
                    ], capture_output=True, text=True, check=False)
                    
                    if result.returncode == 0:
                        self.logger.info(f"✅ Deleted project: {project_title}")
                        self.stats['projects_deleted'] += 1
                    else:
                        self.logger.warning(f"⚠️ Failed to delete project {project_title}: {result.stderr}")
                        self.stats['errors'] += 1
                    
                    # Small delay to avoid rate limiting
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.logger.error(f"Error deleting project {project_title}: {e}")
                    self.stats['errors'] += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete projects: {e}")
            return False
    
    def delete_repositories(self, repositories: List[Dict]) -> bool:
        """Delete all repositories"""
        try:
            if not repositories:
                self.logger.info("No repositories to delete")
                return True
            
            self.logger.info(f"Deleting {len(repositories)} repositories...")
            
            for repo in repositories:
                repo_name = repo['name']
                
                if self.dry_run:
                    self.logger.info(f"[DRY RUN] Would delete repository: {repo_name}")
                    self.stats['repositories_deleted'] += 1
                    continue
                
                try:
                    result = subprocess.run([
                        'gh', 'repo', 'delete', f"{self.org_name}/{repo_name}", '--yes'
                    ], capture_output=True, text=True, check=False)
                    
                    if result.returncode == 0:
                        self.logger.info(f"✅ Deleted repository: {repo_name}")
                        self.stats['repositories_deleted'] += 1
                    else:
                        self.logger.warning(f"⚠️ Failed to delete repository {repo_name}: {result.stderr}")
                        self.stats['errors'] += 1
                    
                    # Small delay to avoid rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"Error deleting repository {repo_name}: {e}")
                    self.stats['errors'] += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete repositories: {e}")
            return False
    
    def close_issues(self, issues: List[Dict]) -> bool:
        """Close all open issues"""
        try:
            if not issues:
                self.logger.info("No issues to close")
                return True
            
            open_issues = [i for i in issues if i.get('state') == 'open']
            if not open_issues:
                self.logger.info("No open issues to close")
                return True
            
            self.logger.info(f"Closing {len(open_issues)} open issues...")
            
            for issue in open_issues:
                repo_name = issue['repository']
                issue_number = issue['number']
                issue_title = issue.get('title', 'Unknown')
                
                if self.dry_run:
                    self.logger.info(f"[DRY RUN] Would close issue: {repo_name}#{issue_number} - {issue_title}")
                    self.stats['issues_deleted'] += 1
                    continue
                
                try:
                    result = subprocess.run([
                        'gh', 'issue', 'close', str(issue_number), 
                        '--repo', f"{self.org_name}/{repo_name}",
                        '--comment', 'Closing issue as part of organization cleanup'
                    ], capture_output=True, text=True, check=False)
                    
                    if result.returncode == 0:
                        self.logger.info(f"✅ Closed issue: {repo_name}#{issue_number}")
                        self.stats['issues_deleted'] += 1
                    else:
                        self.logger.warning(f"⚠️ Failed to close issue {repo_name}#{issue_number}: {result.stderr}")
                        self.stats['errors'] += 1
                    
                    # Small delay to avoid rate limiting
                    time.sleep(0.3)
                    
                except Exception as e:
                    self.logger.error(f"Error closing issue {repo_name}#{issue_number}: {e}")
                    self.stats['errors'] += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to close issues: {e}")
            return False
    
    def reset_teams(self, teams: List[Dict]) -> bool:
        """Reset organization teams"""
        try:
            if not teams:
                self.logger.info("No teams to reset")
                return True
            
            self.logger.info(f"Resetting {len(teams)} teams...")
            
            for team in teams:
                team_slug = team['slug']
                team_name = team['name']
                
                if self.dry_run:
                    self.logger.info(f"[DRY RUN] Would reset team: {team_name}")
                    self.stats['teams_cleaned'] += 1
                    continue
                
                try:
                    # Remove all repositories from team
                    result = subprocess.run([
                        'gh', 'api', f'/orgs/{self.org_name}/teams/{team_slug}/repos'
                    ], capture_output=True, text=True, check=False)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        repos = json.loads(result.stdout)
                        for repo in repos:
                            subprocess.run([
                                'gh', 'api', f'/orgs/{self.org_name}/teams/{team_slug}/repos/{self.org_name}/{repo["name"]}',
                                '-X', 'DELETE'
                            ], capture_output=True, text=True, check=False)
                    
                    self.logger.info(f"✅ Reset team: {team_name}")
                    self.stats['teams_cleaned'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error resetting team {team_name}: {e}")
                    self.stats['errors'] += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reset teams: {e}")
            return False
    
    def save_cleanup_report(self) -> None:
        """Save cleanup report to file"""
        try:
            report = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'organization': self.org_name,
                'dry_run': self.dry_run,
                'statistics': self.stats,
                'success': self.stats['errors'] == 0
            }
            
            report_file = Path(f'cleanup-report-{self.org_name}.json')
            report_file.write_text(json.dumps(report, indent=2))
            
            self.logger.info(f"Cleanup report saved to: {report_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save cleanup report: {e}")
    
    def cleanup_organization(self) -> bool:
        """Perform complete organization cleanup"""
        try:
            self.logger.info(f"Starting organization cleanup: {self.org_name}")
            self.logger.info(f"Dry run mode: {self.dry_run}")
            
            if not self.validate_prerequisites():
                return False
            
            # Get inventory
            inventory = self.get_organization_inventory()
            
            if self.dry_run:
                self.logger.info("=== DRY RUN MODE - NO ACTUAL CHANGES WILL BE MADE ===")
            else:
                self.logger.warning("=== LIVE MODE - DELETING ORGANIZATION RESOURCES ===")
                time.sleep(3)  # Give user time to cancel
            
            # Clean up in order: issues -> projects -> repositories -> teams
            success = True
            
            # 1. Close issues first
            if not self.close_issues(inventory['issues']):
                success = False
            
            # 2. Delete projects
            if not self.delete_projects(inventory['projects']):
                success = False
            
            # 3. Delete repositories
            if not self.delete_repositories(inventory['repositories']):
                success = False
            
            # 4. Reset teams
            if not self.reset_teams(inventory['teams']):
                success = False
            
            # Generate report
            self.save_cleanup_report()
            
            # Summary
            self.logger.info("=== CLEANUP SUMMARY ===")
            self.logger.info(f"Projects deleted: {self.stats['projects_deleted']}")
            self.logger.info(f"Repositories deleted: {self.stats['repositories_deleted']}")
            self.logger.info(f"Issues closed: {self.stats['issues_deleted']}")
            self.logger.info(f"Teams cleaned: {self.stats['teams_cleaned']}")
            self.logger.info(f"Errors: {self.stats['errors']}")
            
            if success:
                self.logger.info("✅ Organization cleanup completed successfully")
                if not self.dry_run:
                    self.logger.info(f"Organization {self.org_name} is now clean and ready for rebuild")
            else:
                self.logger.error("❌ Organization cleanup completed with errors")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Organization cleanup failed: {e}")
            return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="GitHub Organization Cleanup Script",
        epilog="WARNING: This script will delete all data in the organization!"
    )
    
    parser.add_argument(
        '--org',
        default='AI-DevOps-Org-2025',
        help='GitHub organization name (default: AI-DevOps-Org-2025)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what will be deleted without making changes'
    )
    
    parser.add_argument(
        '--confirm-deletion',
        action='store_true',
        help='Required to actually delete resources (safety flag)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Safety check
    if not args.dry_run and not args.confirm_deletion:
        print("ERROR: Must specify either --dry-run or --confirm-deletion")
        print("Use --dry-run to preview changes, or --confirm-deletion to actually delete resources")
        sys.exit(1)
    
    if not args.dry_run:
        print(f"WARNING: This will DELETE ALL DATA in organization '{args.org}'")
        print("This action cannot be undone!")
        response = input("Type 'DELETE' to confirm: ")
        if response != 'DELETE':
            print("Operation cancelled")
            sys.exit(1)
    
    # Initialize cleaner
    cleaner = GitHubOrganizationCleaner(args.org, args.dry_run)
    
    # Perform cleanup
    success = cleaner.cleanup_organization()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
