#!/usr/bin/env python3
import sys, json, hashlib, os

def load_hashes(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # support list or dict of hashes
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return list(data.values())
        return []
    except Exception:
        # corrupted file: start fresh
        return []

def save_hashes(path, hashes):
    # store as list
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(hashes, f, ensure_ascii=False, indent=2)

def main():
    if len(sys.argv) < 2:
        print('Usage: duplicate_detection.py <article_text_file>', file=sys.stderr)
        sys.exit(2)
    article_path = sys.argv[1]
    try:
        with open(article_path, 'r', encoding='utf-8') as f:
            body = f.read()
    except Exception as e:
        print(f'Failed to read article file: {e}', file=sys.stderr)
        sys.exit(3)
    sha256 = hashlib.sha256(body.encode('utf-8')).hexdigest()
    db_path = os.path.join(os.path.dirname(__file__), 'hashes.db')
    hashes = load_hashes(db_path)
    if sha256 in hashes:
        print('duplicate')
        sys.exit(0)
    hashes.append(sha256)
    save_hashes(db_path, hashes)
    print('new')
    sys.exit(0)

if __name__ == '__main__':
    main()
