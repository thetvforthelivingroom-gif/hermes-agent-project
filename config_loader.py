# config_loader.py
"""Simple configuration loader for News_Ag.
Supports YAML-like syntax with comments and simple key/value pairs.
Falls back to a minimal parser if PyYAML is unavailable.
"""

import os
import json

def _parse_simple_yaml(content: str) -> dict:
    """Very lightweight parser for the subset used in config.example.yaml.
    Handles scalar values, booleans, integers, and simple lists.
    """
    result = {}
    lines = content.splitlines()
    current_key = None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped.startswith('- '):
            # List item for the most recent key
            if current_key is None:
                continue
            val = stripped[2:].strip('"')
            result.setdefault(current_key, []).append(val)
            continue
        if ':' in stripped:
            key, raw_val = stripped.split(':', 1)
            key = key.strip()
            raw_val = raw_val.strip()
            # Strip surrounding quotes
            if raw_val.startswith('"') and raw_val.endswith('"'):
                raw_val = raw_val[1:-1]
            # Type conversion
            if raw_val.lower() in ('true', 'false'):
                val = raw_val.lower() == 'true'
            else:
                try:
                    val = int(raw_val)
                except ValueError:
                    val = raw_val
            result[key] = val
            current_key = key if isinstance(val, list) else None
            continue
    return result

def load_config(path: str = None) -> dict:
    """Load configuration.
    If `path` is None, looks for `config.yaml` in the current working directory.
    Falls back to `config.example.yaml` if the file is missing.
    Returns a dict with defaults applied.
    """
    if path is None:
        path = os.path.join(os.getcwd(), 'config.yaml')
    if not os.path.isfile(path):
        example_path = os.path.join(os.getcwd(), 'config.example.yaml')
        if os.path.isfile(example_path):
            path = example_path
        else:
            raise FileNotFoundError('No configuration file found')
    try:
        import yaml  # type: ignore
        with open(path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        # Fallback simple parser
        with open(path, 'r', encoding='utf-8') as f:
            raw = f.read()
        cfg = _parse_simple_yaml(raw)
    # Apply defaults
    defaults = {
        'output_dir': './site',
        'max_articles': 10,
        'fetch_images': True,
        'source_whitelist': [],
    }
    for k, v in defaults.items():
        cfg.setdefault(k, v)
    return cfg
