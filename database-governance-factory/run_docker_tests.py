#!/usr/bin/env python3
"""
Comprehensive Docker-based test runner for Database Governance Factory
Executes all tests in containerized environment with proper database setup
"""

import subprocess
import sys
import time
import json
import os
from pathlib import Path

class DockerTestRunner:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.compose_file = "docker-compose.test.yml"
        
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def run_command(self, command: list, check: bool = True) -> subprocess.CompletedProcess:
        """Run shell command and return result"""
        self.log(f"Executing: {' '.join(command)}")
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e}", "ERROR")
            self.log(f"STDOUT: {e.stdout}", "ERROR")
            self.log(f"STDERR: {e.stderr}", "ERROR")
            raise
            
    def check_docker(self):
        """Verify Docker is available and running"""
        self.log("Checking Docker availability...")
        try:
            result = self.run_command(["docker", "version"])
            self.log("Docker is available")
            
            result = self.run_command(["docker", "compose", "version"])
            self.log("Docker Compose is available")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("Docker or Docker Compose not available", "ERROR")
            return False
            
    def cleanup_containers(self):
        """Clean up any existing test containers"""
        self.log("Cleaning up existing test containers...")
        try:
            self.run_command([
                "docker", "compose", 
                "-f", self.compose_file,
                "down", "-v", "--remove-orphans"
            ], check=False)
            self.log("Cleanup completed")
        except Exception as e:
            self.log(f"Cleanup warning: {e}", "WARN")
            
    def build_test_images(self):
        """Build test Docker images"""
        self.log("Building test Docker images...")
        result = self.run_command([
            "docker", "compose",
            "-f", self.compose_file,
            "build", "--no-cache"
        ])
        self.log("Test images built successfully")
        return result.returncode == 0
        
    def start_databases(self):
        """Start test database services"""
        self.log("Starting test database services...")
        result = self.run_command([
            "docker", "compose",
            "-f", self.compose_file,
            "up", "-d",
            "test-mongodb", "test-postgresql", "test-redis"
        ])
        
        # Wait for databases to be healthy
        self.log("Waiting for databases to be ready...")
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Check health status
                result = self.run_command([
                    "docker", "compose",
                    "-f", self.compose_file,
                    "ps", "--format", "json"
                ], check=False)
                
                if result.returncode == 0:
                    services = []
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            services.append(json.loads(line))
                    
                    db_services = [s for s in services if s['Service'].startswith('test-')]
                    healthy_services = [s for s in db_services if 'healthy' in s.get('State', '')]
                    
                    self.log(f"Healthy services: {len(healthy_services)}/{len(db_services)}")
                    
                    if len(healthy_services) == len(db_services):
                        self.log("All database services are healthy")
                        return True
                        
            except Exception as e:
                self.log(f"Health check attempt {attempt + 1} failed: {e}", "WARN")
                
            attempt += 1
            time.sleep(5)
            
        self.log("Databases failed to become healthy within timeout", "ERROR")
        return False
        
    def run_unit_tests(self):
        """Run unit tests in container"""
        self.log("Running unit tests...")
        result = self.run_command([
            "docker", "compose",
            "-f", self.compose_file,
            "run", "--rm",
            "test-runner",
            "python", "-m", "pytest", "tests/", "-v", "--tb=short", "--durations=10"
        ])
        
        success = result.returncode == 0
        if success:
            self.log("Unit tests passed")
        else:
            self.log("Unit tests failed", "ERROR")
            
        return success
        
    def run_system_tests(self):
        """Run system integration tests"""
        self.log("Running system integration tests...")
        result = self.run_command([
            "docker", "compose",
            "-f", self.compose_file,
            "run", "--rm",
            "test-runner",
            "python", "test_system.py"
        ])
        
        success = result.returncode == 0
        if success:
            self.log("System tests passed")
        else:
            self.log("System tests failed", "ERROR")
            
        return success
        
    def run_api_tests(self):
        """Run API integration tests"""
        self.log("Starting test API service...")
        
        # Start API service
        self.run_command([
            "docker", "compose",
            "-f", self.compose_file,
            "up", "-d", "test-api"
        ])
        
        # Wait for API to be ready
        self.log("Waiting for API to be ready...")
        time.sleep(10)
        
        # Run API tests
        self.log("Running API integration tests...")
        result = self.run_command([
            "docker", "compose",
            "-f", self.compose_file,
            "run", "--rm",
            "test-runner",
            "python", "-m", "pytest", "tests/test_api_integration.py", "-v"
        ], check=False)
        
        success = result.returncode == 0
        if success:
            self.log("API tests passed")
        else:
            self.log("API tests failed", "ERROR")
            
        return success
        
    def run_performance_tests(self):
        """Run performance benchmarks"""
        self.log("Running performance tests...")
        result = self.run_command([
            "docker", "compose",
            "-f", self.compose_file,
            "run", "--rm",
            "test-runner",
            "python", "-m", "pytest", "tests/test_performance.py", "-v", "--benchmark-only"
        ], check=False)
        
        success = result.returncode == 0
        if success:
            self.log("Performance tests completed")
        else:
            self.log("Performance tests failed", "ERROR")
            
        return success
        
    def collect_logs(self):
        """Collect logs from test containers"""
        self.log("Collecting test logs...")
        
        log_dir = self.project_root / "test_results" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        services = ["test-mongodb", "test-postgresql", "test-redis", "test-api"]
        
        for service in services:
            try:
                result = self.run_command([
                    "docker", "compose",
                    "-f", self.compose_file,
                    "logs", service
                ], check=False)
                
                log_file = log_dir / f"{service}.log"
                with open(log_file, "w") as f:
                    f.write(result.stdout)
                    f.write(result.stderr)
                    
                self.log(f"Collected logs for {service}")
                
            except Exception as e:
                self.log(f"Failed to collect logs for {service}: {e}", "WARN")
                
    def generate_report(self, results: dict):
        """Generate test report"""
        self.log("Generating test report...")
        
        report_dir = self.project_root / "test_results"
        report_dir.mkdir(exist_ok=True)
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "environment": "docker",
            "results": results,
            "summary": {
                "total_suites": len(results),
                "passed_suites": sum(1 for r in results.values() if r),
                "failed_suites": sum(1 for r in results.values() if not r),
                "overall_success": all(results.values())
            }
        }
        
        report_file = report_dir / "test_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
            
        self.log(f"Test report saved to {report_file}")
        return report
        
    def run_all_tests(self):
        """Run complete test suite"""
        self.log("Starting comprehensive Docker-based testing...")
        
        if not self.check_docker():
            return False
            
        try:
            # Setup
            self.cleanup_containers()
            
            if not self.build_test_images():
                return False
                
            if not self.start_databases():
                return False
                
            # Run test suites
            results = {}
            
            results["unit_tests"] = self.run_unit_tests()
            results["system_tests"] = self.run_system_tests()
            results["api_tests"] = self.run_api_tests()
            results["performance_tests"] = self.run_performance_tests()
            
            # Collect artifacts
            self.collect_logs()
            report = self.generate_report(results)
            
            # Print summary
            self.log("=== TEST SUMMARY ===")
            for suite, passed in results.items():
                status = "PASSED" if passed else "FAILED"
                self.log(f"{suite}: {status}")
                
            overall_success = all(results.values())
            self.log(f"Overall result: {'SUCCESS' if overall_success else 'FAILURE'}")
            
            return overall_success
            
        except Exception as e:
            self.log(f"Test execution failed: {e}", "ERROR")
            return False
            
        finally:
            # Cleanup
            self.log("Cleaning up test environment...")
            self.cleanup_containers()

def main():
    """Main entry point"""
    runner = DockerTestRunner()
    
    if len(sys.argv) > 1:
        # Run specific test suite
        test_type = sys.argv[1]
        
        if not runner.check_docker():
            sys.exit(1)
            
        runner.cleanup_containers()
        runner.build_test_images()
        runner.start_databases()
        
        if test_type == "unit":
            success = runner.run_unit_tests()
        elif test_type == "system":
            success = runner.run_system_tests()
        elif test_type == "api":
            success = runner.run_api_tests()
        elif test_type == "performance":
            success = runner.run_performance_tests()
        else:
            runner.log(f"Unknown test type: {test_type}", "ERROR")
            success = False
            
        runner.cleanup_containers()
        sys.exit(0 if success else 1)
    else:
        # Run all tests
        success = runner.run_all_tests()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
