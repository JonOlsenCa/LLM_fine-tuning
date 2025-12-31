"""Scan project for secrets and credentials."""
import os
import re
from pathlib import Path

secrets_patterns = [
    (r'sk-[a-zA-Z0-9]{20,}', 'OpenAI API Key'),
    (r'ghp_[a-zA-Z0-9]{30,}', 'GitHub Token'),
    (r'hf_[a-zA-Z0-9]{30,}', 'HuggingFace Token'),
    (r'Server\s*=.*Password\s*=', 'Connection String'),
    (r'OPENAI_API_KEY\s*=\s*["\']?[^"\'\s]{10,}', 'OpenAI Key Assignment'),
    (r'HF_TOKEN\s*=\s*["\']?[^"\'\s]{10,}', 'HF Token Assignment'),
    (r'api_key\s*[=:]\s*["\'][^"\']{10,}', 'API Key'),
]

exclude_dirs = {'.venv', 'venv', '.git', '__pycache__', 'node_modules', '.tox', 'site-packages'}
include_ext = {'.py', '.ps1', '.yaml', '.yml', '.json', '.env', '.ini', '.config', '.txt'}

findings = []

for root, dirs, files in os.walk('.'):
    # Skip excluded directories
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    
    for f in files:
        ext = Path(f).suffix.lower()
        if ext in include_ext or f in ['.env', 'secrets', 'credentials']:
            filepath = os.path.join(root, f)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    for pattern, desc in secrets_patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for m in matches:
                            line_num = content[:m.start()].count('\n') + 1
                            match_text = m.group()[:60]
                            findings.append((filepath, line_num, desc, match_text))
            except Exception:
                pass

print("=" * 70)
print("SECRET/CREDENTIAL SCAN RESULTS")
print("=" * 70)

if findings:
    print(f"\n⚠️  FOUND {len(findings)} POTENTIAL SECRETS:\n")
    for path, line, desc, match in findings:
        print(f"File: {path}")
        print(f"Line: {line}")
        print(f"Type: {desc}")
        print(f"Match: {match}...")
        print("-" * 40)
else:
    print("\n✅ No secrets/credentials found in project files.\n")

# Also check for .env files
print("\n[.ENV FILES]")
env_files = list(Path('.').rglob('.env')) + list(Path('.').rglob('*.env'))
env_files = [f for f in env_files if 'venv' not in str(f) and '.venv' not in str(f)]
if env_files:
    print("Found .env files:")
    for f in env_files:
        print(f"  ⚠️  {f}")
else:
    print("  No .env files found.")

print("\n" + "=" * 70)

