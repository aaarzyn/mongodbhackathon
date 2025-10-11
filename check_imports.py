"""
Quick script to scan our Python files and figure out what packages we need.
Helps us keep requirements.txt accurate.
"""
import re
from pathlib import Path
from collections import defaultdict


def extract_imports(file_path):
    """Pull out all the import statements from a Python file."""
    imports = set()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match "import something"
    import_pattern = r'^import\s+([a-zA-Z0-9_\.]+)'
    # Match "from something import ..."
    from_pattern = r'^from\s+([a-zA-Z0-9_\.]+)\s+import'
    
    for match in re.finditer(import_pattern, content, re.MULTILINE):
        package = match.group(1).split('.')[0]
        imports.add(package)
    
    for match in re.finditer(from_pattern, content, re.MULTILINE):
        package = match.group(1).split('.')[0]
        imports.add(package)
    
    return imports


def scan_directory(directory):
    """Walk through a directory and find all imports in Python files."""
    all_imports = defaultdict(list)
    
    for py_file in Path(directory).rglob('*.py'):
        # Skip cache files
        if '__pycache__' in str(py_file):
            continue
        
        file_imports = extract_imports(py_file)
        for imp in file_imports:
            all_imports[imp].append(str(py_file))
    
    return all_imports


if __name__ == "__main__":
    print("Scanning backend/ for imports...\n")
    
    imports = scan_directory('backend')
    
    # Built-in Python modules we don't need to install
    stdlib = {
        'abc', 'asyncio', 'collections', 'contextlib', 'datetime', 
        'enum', 'functools', 'json', 'logging', 'os', 'pathlib', 're', 
        'sys', 'time', 'typing', 'uuid'
    }
    
    third_party = {}
    stdlib_used = {}
    
    for pkg, files in sorted(imports.items()):
        if pkg in stdlib or pkg.startswith('_'):
            stdlib_used[pkg] = files
        else:
            third_party[pkg] = files
    
    print("=" * 70)
    print("THIRD-PARTY PACKAGES (need to install these)")
    print("=" * 70)
    
    for pkg in sorted(third_party.keys()):
        print(f"  - {pkg}")
        # Show a couple examples of where it's used
        for f in third_party[pkg][:2]:
            print(f"      used in: {f}")
    
    print("\n" + "=" * 70)
    print("STANDARD LIBRARY (already in Python)")
    print("=" * 70)
    
    for pkg in sorted(stdlib_used.keys()):
        print(f"  - {pkg}")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Third-party packages: {len(third_party)}")
    print(f"Standard library modules: {len(stdlib_used)}")
    
    # Some packages have different pip names than import names
    print("\n" + "=" * 70)
    print("PIP INSTALL COMMAND")
    print("=" * 70)
    
    pip_mapping = {
        'pydantic': 'pydantic',
        'pydantic_settings': 'pydantic-settings',
        'pymongo': 'pymongo',
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'email_validator': 'email-validator',
        'dotenv': 'python-dotenv',
        'sentence_transformers': 'sentence-transformers',
        'httpx': 'httpx',
        'sklearn': 'scikit-learn',
        'numpy': 'numpy',
        'click': 'click',
    }
    
    packages_to_install = []
    for pkg in third_party.keys():
        if pkg in pip_mapping:
            packages_to_install.append(pip_mapping[pkg])
        elif pkg != 'backend':  # Don't try to install our own code
            packages_to_install.append(pkg)
    
    if packages_to_install:
        cmd = ' '.join(sorted(set(packages_to_install)))
        print(f"\npip install {cmd}")
    else:
        print("\nNo third-party packages found yet.")