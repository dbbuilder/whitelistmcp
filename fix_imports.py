#!/usr/bin/env python3
"""Remove unused imports from the codebase."""

import ast
import sys
from pathlib import Path
from typing import Set, List, Tuple


def get_imports_and_usage(file_path: Path) -> Tuple[Set[str], Set[str], List[str]]:
    """Get imports and their usage in a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.splitlines()
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        print(f"Syntax error in {file_path}")
        return set(), set(), lines
    
    imports = set()
    used_names = set()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.asname or alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.add(alias.asname or alias.name)
        elif isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)
    
    return imports, used_names, lines


def remove_unused_imports(file_path: Path) -> bool:
    """Remove unused imports from a file."""
    imports, used_names, lines = get_imports_and_usage(file_path)
    
    # Common imports that should not be removed
    keep_imports = {'__future__', 'typing', 'TYPE_CHECKING', 'Any', 'Optional', 
                   'List', 'Dict', 'Union', 'Tuple', 'Set', 'Callable'}
    
    unused = imports - used_names - keep_imports
    
    if not unused:
        return False
    
    print(f"\n{file_path}:")
    print(f"  Unused imports: {', '.join(sorted(unused))}")
    
    # Parse again to find and remove unused import lines
    try:
        tree = ast.parse('\n'.join(lines))
    except SyntaxError:
        return False
    
    lines_to_remove = set()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split('.')[0]
                if name in unused:
                    lines_to_remove.add(node.lineno - 1)
        elif isinstance(node, ast.ImportFrom):
            # Check if all imports from this line are unused
            all_unused = True
            for alias in node.names:
                name = alias.asname or alias.name
                if name not in unused:
                    all_unused = False
                    break
            if all_unused:
                lines_to_remove.add(node.lineno - 1)
    
    # Remove lines
    new_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print(f"  Removed {len(lines_to_remove)} import lines")
    return True


def main():
    """Main function."""
    root = Path("whitelistmcp")
    fixed_count = 0
    
    for file_path in root.rglob("*.py"):
        if "__pycache__" not in str(file_path):
            if remove_unused_imports(file_path):
                fixed_count += 1
    
    print(f"\n✅ Fixed {fixed_count} files")


if __name__ == "__main__":
    main()