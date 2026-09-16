#!/usr/bin/env python3
import sys
import re
from pathlib import Path
import subprocess

KANBAN_FILE = Path('kanban.md')

def load_lines():
    return KANBAN_FILE.read_text(encoding='utf-8').splitlines()

def save_lines(lines):
    KANBAN_FILE.write_text('\n'.join(lines) + '\n', encoding='utf-8')

def find_section(lines, title):
    pattern = re.compile(r'^##\s*' + re.escape(title) + r'\s*$')
    for i, line in enumerate(lines):
        if pattern.match(line.strip()):
            return i
    return None

def move_first_todo_to_inprogress():
    # Import error logging utility
    from error_logging import log_error
    # Helper to log subprocess failures
    def _run_subprocess(cmd):
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            log_error('run_pipeline subprocess', e.returncode, str(e))
            raise
    # End helper
    
    lines = load_lines()
    todo_idx = find_section(lines, 'To-Do')
    if todo_idx is None:
        print('No To-Do section found', file=sys.stderr)
        return False
    # Find first bullet after the heading
    for i in range(todo_idx + 1, len(lines)):
        line = lines[i]
        if line.strip() == '' or line.startswith('#'):
            continue
        if line.lstrip().startswith('- '):
            url = line.lstrip()[2:].strip()
            # Remove this line
            del lines[i]
            # Ensure In-Progress section exists
            inprog_idx = find_section(lines, 'In-Progress')
            if inprog_idx is None:
                # Insert after To-Do section plus a blank line
                insert_at = todo_idx + 1
                lines.insert(insert_at, '')
                lines.insert(insert_at + 1, '## In-Progress')
                inprog_idx = insert_at + 1
            # Insert URL under In-Progress (after heading)
            insert_at = inprog_idx + 1
            # Skip existing blank lines
            while insert_at < len(lines) and lines[insert_at].strip() == '':
                insert_at += 1
            lines.insert(insert_at, f'- {url}')
            save_lines(lines)
            # Spawn research_agent.py
            try:
                _run_subprocess([sys.executable, 'research_agent.py', url])

            except FileNotFoundError:
                print('research_agent.py not found', file=sys.stderr)
            except subprocess.CalledProcessError as e:
                print('research_agent.py failed', e, file=sys.stderr)
            return True
        # Stop if another heading encountered
        if line.startswith('##'):
            break
    print('No URL found in To-Do', file=sys.stderr)
    return False

if __name__ == '__main__':
    moved = move_first_todo_to_inprogress()
    sys.exit(0 if moved else 1)
