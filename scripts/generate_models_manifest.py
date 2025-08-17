#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(REPO_ROOT, 'models')
OUT_DIR = os.path.join(REPO_ROOT, 'docs', 'data')
OUT_FILE = os.path.join(OUT_DIR, 'models_index.json')

KNOWN_FILES = [
    'metadata.json',
    'parameters.json',
    'prompting.md',
    'pitfalls.md',
    'cost_optimization.md',
]

def read_json_safe(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

def collect_models():
    items = []
    if not os.path.isdir(MODELS_DIR):
        return items
    for category in sorted(os.listdir(MODELS_DIR)):
        cat_path = os.path.join(MODELS_DIR, category)
        if not os.path.isdir(cat_path):
            continue
        for model in sorted(os.listdir(cat_path)):
            model_path = os.path.join(cat_path, model)
            if not os.path.isdir(model_path):
                continue
            data = {
                'category': category,
                'model': model,
                'title': None,
                'tags': None,
                'summary': None,
                'paths': {}
            }
            meta = read_json_safe(os.path.join(model_path, 'metadata.json'))
            if meta:
                data['title'] = meta.get('name') or model
                data['tags'] = meta.get('tags')
                data['summary'] = meta.get('description') or meta.get('summary')
            else:
                data['title'] = model

            for fname in KNOWN_FILES:
                fpath = os.path.join(model_path, fname)
                if os.path.isfile(fpath):
                    # Paths are absolute from site root where website will host a copy under /models/
                    data['paths'][os.path.splitext(fname)[0]] = f"/models/{category}/{model}/{fname}"

            # Also include any extra .md files as generic entries
            try:
                for extra in os.listdir(model_path):
                    if extra.endswith('.md') and extra not in KNOWN_FILES:
                        data['paths'][os.path.splitext(extra)[0]] = f"/models/{category}/{model}/{extra}"
            except OSError:
                pass

            items.append(data)
    return items

def main():
    items = collect_models()
    os.makedirs(OUT_DIR, exist_ok=True)
    payload = {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'items': items,
    }
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_FILE} with {len(items)} items")

if __name__ == '__main__':
    sys.exit(main())


