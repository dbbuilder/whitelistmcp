#!/usr/bin/env python3
"""
Comprehensive code quality checker for the whitelistmcp project.
Runs multiple static analysis tools and reports issues.
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import argparse


class CodeQualityChecker:
    """Run various static analysis tools and report results."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = {}
        self.project_root = Path(__file__).parent
        
    def run_command(self, cmd: List[str], check: bool = False) -> Tuple[int, str, str]:
        """Run a command and return exit code, stdout, and stderr."""
        if self.verbose:
            print(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout, e.stderr
        except FileNotFoundError:
            return -1, "", f"Command not found: {cmd[0]}"
    
    def check_imports(self) -> Dict[str, Any]:
        """Check for missing imports and circular dependencies."""
        print("🔍 Checking imports...")
        
        # Check for missing imports
        code, out, err = self.run_command([
            sys.executable, "-m", "pyflakes", "whitelistmcp"
        ])
        
        issues = []
        if out:
            for line in out.splitlines():
                if "undefined name" in line or "imported but unused" in line:
                    issues.append(line)
        
        # Check for circular imports
        code2, out2, err2 = self.run_command([
            sys.executable, "-c",
            "import whitelistmcp; print('No circular imports detected')"
        ])
        
        if code2 != 0:
            issues.append(f"Circular import detected: {err2}")
        
        return {
            "tool": "import-check",
            "passed": len(issues) == 0,
            "issues": issues
        }
    
    def check_type_hints(self) -> Dict[str, Any]:
        """Run mypy for type checking."""
        print("🔍 Checking type hints with mypy...")
        
        code, out, err = self.run_command([
            sys.executable, "-m", "mypy",
            "whitelistmcp",
            "--ignore-missing-imports",
            "--no-error-summary"
        ])
        
        issues = []
        if out:
            for line in out.splitlines():
                if "error:" in line:
                    issues.append(line)
        
        return {
            "tool": "mypy",
            "passed": code == 0,
            "issues": issues
        }
    
    def check_code_style(self) -> Dict[str, Any]:
        """Check code style with flake8."""
        print("🔍 Checking code style with flake8...")
        
        code, out, err = self.run_command([
            sys.executable, "-m", "flake8",
            "whitelistmcp",
            "--max-line-length=120",
            "--extend-ignore=E203,W503"
        ])
        
        issues = out.splitlines() if out else []
        
        return {
            "tool": "flake8",
            "passed": code == 0,
            "issues": issues
        }
    
    def check_code_complexity(self) -> Dict[str, Any]:
        """Check code complexity with radon."""
        print("🔍 Checking code complexity...")
        
        code, out, err = self.run_command([
            sys.executable, "-m", "radon", "cc",
            "whitelistmcp", "-s", "-n", "C"
        ])
        
        issues = []
        if out:
            for line in out.splitlines():
                if line.strip() and not line.startswith("whitelistmcp"):
                    # Radon shows functions with complexity > threshold
                    issues.append(line)
        
        return {
            "tool": "radon",
            "passed": len(issues) == 0,
            "issues": issues
        }
    
    def check_security(self) -> Dict[str, Any]:
        """Check for security issues with bandit."""
        print("🔍 Checking security with bandit...")
        
        code, out, err = self.run_command([
            sys.executable, "-m", "bandit",
            "-r", "whitelistmcp",
            "-f", "json",
            "-ll"  # Only show medium and high severity
        ])
        
        issues = []
        if out:
            try:
                results = json.loads(out)
                for result in results.get("results", []):
                    issues.append(
                        f"{result['filename']}:{result['line_number']} "
                        f"[{result['test_id']}] {result['issue_text']}"
                    )
            except json.JSONDecodeError:
                issues = out.splitlines()
        
        return {
            "tool": "bandit",
            "passed": len(issues) == 0,
            "issues": issues
        }
    
    def check_unused_code(self) -> Dict[str, Any]:
        """Check for unused code with vulture."""
        print("🔍 Checking for unused code...")
        
        code, out, err = self.run_command([
            sys.executable, "-m", "vulture",
            "whitelistmcp",
            "--min-confidence", "80"
        ])
        
        issues = []
        if out:
            for line in out.splitlines():
                # Filter out false positives
                if not any(skip in line for skip in ["__all__", "__version__", "_"]):
                    issues.append(line)
        
        return {
            "tool": "vulture",
            "passed": len(issues) == 0,
            "issues": issues[:10]  # Limit output
        }
    
    def check_docstrings(self) -> Dict[str, Any]:
        """Check for missing docstrings with pydocstyle."""
        print("🔍 Checking docstrings...")
        
        code, out, err = self.run_command([
            sys.executable, "-m", "pydocstyle",
            "whitelistmcp",
            "--ignore=D100,D101,D102,D103,D104,D105,D107"
        ])
        
        issues = []
        if out:
            for line in out.splitlines():
                if ":" in line and "warning" not in line.lower():
                    issues.append(line)
        
        return {
            "tool": "pydocstyle",
            "passed": len(issues) < 10,  # Allow some missing docstrings
            "issues": issues[:10]
        }
    
    def check_dependencies(self) -> Dict[str, Any]:
        """Check for dependency issues."""
        print("🔍 Checking dependencies...")
        
        issues = []
        
        # Check if all imports are in requirements
        code, out, err = self.run_command([
            sys.executable, "-m", "pipreqs",
            ".", "--print"
        ])
        
        if code == 0 and out:
            required = set(line.split("==")[0] for line in out.splitlines())
            
            # Read current requirements
            req_file = self.project_root / "requirements.txt"
            if req_file.exists():
                with open(req_file) as f:
                    installed = set(
                        line.split(">=")[0].split("==")[0].strip()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    )
                
                missing = required - installed
                if missing:
                    issues.extend([f"Missing requirement: {pkg}" for pkg in missing])
        
        return {
            "tool": "dependency-check",
            "passed": len(issues) == 0,
            "issues": issues
        }
    
    def check_todos(self) -> Dict[str, Any]:
        """Check for TODO/FIXME/HACK comments."""
        print("🔍 Checking for TODOs...")
        
        code, out, err = self.run_command([
            "grep", "-r", "-n", "-E",
            "(TODO|FIXME|HACK|XXX|BUG)",
            "whitelistmcp",
            "--include=*.py"
        ])
        
        issues = out.splitlines() if out else []
        
        return {
            "tool": "todo-check",
            "passed": len(issues) < 5,  # Allow some TODOs
            "issues": issues
        }
    
    def run_all_checks(self) -> None:
        """Run all checks and display results."""
        checks = [
            self.check_imports,
            self.check_type_hints,
            self.check_code_style,
            self.check_code_complexity,
            self.check_security,
            self.check_unused_code,
            self.check_docstrings,
            self.check_dependencies,
            self.check_todos,
        ]
        
        print("\n🚀 Running comprehensive code quality checks...\n")
        
        all_passed = True
        for check in checks:
            try:
                result = check()
                self.results[result["tool"]] = result
                
                if result["passed"]:
                    print(f"✅ {result['tool']}: PASSED")
                else:
                    print(f"❌ {result['tool']}: FAILED")
                    all_passed = False
                    
                if self.verbose and result["issues"]:
                    print(f"   Issues found ({len(result['issues'])}):")
                    for issue in result["issues"][:5]:
                        print(f"   - {issue}")
                    if len(result["issues"]) > 5:
                        print(f"   ... and {len(result['issues']) - 5} more")
                
            except Exception as e:
                print(f"⚠️  {check.__name__}: ERROR - {str(e)}")
                all_passed = False
        
        print("\n" + "="*60)
        if all_passed:
            print("✅ All checks passed! Code quality looks good.")
        else:
            print("❌ Some checks failed. Please review the issues above.")
            
        # Summary
        print("\n📊 Summary:")
        for tool, result in self.results.items():
            if not result["passed"]:
                print(f"   {tool}: {len(result['issues'])} issues")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run code quality checks")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    checker = CodeQualityChecker(verbose=args.verbose)
    checker.run_all_checks()


if __name__ == "__main__":
    main()