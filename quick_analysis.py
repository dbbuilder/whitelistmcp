#!/usr/bin/env python3
"""Quick static analysis without external dependencies."""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple


class QuickAnalyzer:
    """Perform quick static analysis using only stdlib."""
    
    def __init__(self, root_dir: str = "whitelistmcp"):
        self.root_dir = Path(root_dir)
        self.issues: Dict[str, List[str]] = {
            "missing_type_hints": [],
            "missing_docstrings": [],
            "long_lines": [],
            "unused_imports": [],
            "potential_security": [],
            "complexity": []
        }
    
    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
        
        # Check for long lines
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                self.issues["long_lines"].append(f"{file_path}:{i} - {len(line)} chars")
        
        # Parse AST for deeper analysis
        try:
            tree = ast.parse(content, filename=str(file_path))
            self.analyze_ast(tree, file_path)
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
    
    def analyze_ast(self, tree: ast.AST, file_path: Path) -> None:
        """Analyze the AST of a file."""
        # Check imports
        imports: Set[str] = set()
        used_names: Set[str] = set()
        
        for node in ast.walk(tree):
            # Collect imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
                for alias in node.names:
                    imports.add(alias.name)
            
            # Collect used names
            elif isinstance(node, ast.Name):
                used_names.add(node.id)
            
            # Check functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check for type hints
                if not node.returns and node.name != "__init__":
                    self.issues["missing_type_hints"].append(
                        f"{file_path}:{node.lineno} - {node.name}() missing return type"
                    )
                
                # Check for docstrings
                if not ast.get_docstring(node):
                    self.issues["missing_docstrings"].append(
                        f"{file_path}:{node.lineno} - {node.name}() missing docstring"
                    )
                
                # Check complexity (McCabe-like)
                complexity = self.calculate_complexity(node)
                if complexity > 10:
                    self.issues["complexity"].append(
                        f"{file_path}:{node.lineno} - {node.name}() complexity: {complexity}"
                    )
        
        # Find unused imports (simple check)
        unused = imports - used_names - {'__future__', 'typing'}
        for imp in unused:
            self.issues["unused_imports"].append(f"{file_path} - unused import: {imp}")
    
    def calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
    
    def check_security_patterns(self, file_path: Path) -> None:
        """Check for potential security issues."""
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                # Check for hardcoded secrets
                if any(word in line.lower() for word in ['password=', 'secret=', 'token=', 'key=']):
                    if not any(skip in line for skip in ['def ', 'param', 'description', '#']):
                        self.issues["potential_security"].append(
                            f"{file_path}:{i} - Potential hardcoded secret"
                        )
                
                # Check for SQL injection risks
                if 'execute(' in line and '%' in line:
                    self.issues["potential_security"].append(
                        f"{file_path}:{i} - Potential SQL injection risk"
                    )
    
    def analyze_all(self) -> None:
        """Analyze all Python files in the project."""
        for file_path in self.root_dir.rglob("*.py"):
            if "__pycache__" not in str(file_path):
                self.analyze_file(file_path)
                self.check_security_patterns(file_path)
    
    def print_report(self) -> None:
        """Print analysis report."""
        print("=" * 60)
        print("STATIC ANALYSIS REPORT")
        print("=" * 60)
        print()
        
        total_issues = 0
        for issue_type, issues in self.issues.items():
            if issues:
                print(f"🔍 {issue_type.replace('_', ' ').title()} ({len(issues)} issues)")
                for issue in issues[:5]:  # Show first 5
                    print(f"   - {issue}")
                if len(issues) > 5:
                    print(f"   ... and {len(issues) - 5} more")
                print()
                total_issues += len(issues)
        
        if total_issues == 0:
            print("✅ No issues found!")
        else:
            print(f"Total issues: {total_issues}")
        
        print("\nRecommendations:")
        if self.issues["missing_type_hints"]:
            print("- Add type hints to improve code clarity and catch bugs")
        if self.issues["long_lines"]:
            print("- Break long lines to improve readability (max 120 chars)")
        if self.issues["complexity"]:
            print("- Refactor complex functions to reduce cyclomatic complexity")
        if self.issues["potential_security"]:
            print("- Review potential security issues and use environment variables for secrets")


if __name__ == "__main__":
    analyzer = QuickAnalyzer()
    analyzer.analyze_all()
    analyzer.print_report()