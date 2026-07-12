import os
import subprocess
from collections import defaultdict
from datetime import datetime

# Source code extensions only (excluding data like .json, .csv, .ifc, and docs like .md, .pdf)
CODE_EXTENSIONS = {'.py', '.js', '.html', '.css', '.ts', '.jsx', '.tsx', '.sql', '.sh'}

# Substrings that identify a path as library/generated code rather than handwritten
LIBRARY_SUBSTRINGS = ['venv/', '.venv/', 'node_modules/', 'site-packages/', 'migrations/', '__pycache__/', 'vendor/']

def is_handwritten_code(filepath):
    filepath_lower = filepath.lower().replace('\\', '/')
    ext = os.path.splitext(filepath_lower)[1]
    
    if ext not in CODE_EXTENSIONS:
        return False
        
    if any(lib in filepath_lower for lib in LIBRARY_SUBSTRINGS):
        return False
        
    return True

def count_lines_in_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def get_historical_loc(grouping='month'):
    try:
        subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], 
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        
        result = subprocess.run(
            ['git', 'log', '--pretty=tformat:%ad', '--date=short', '--numstat'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        
        period_data = defaultdict(lambda: {'added': 0, 'removed': 0})
        current_period = None
        
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # Match date line strictly
            if len(line) == 10 and line[4] == '-' and line[7] == '-' and line[:4].isdigit():
                if grouping == 'month':
                    current_period = line[:7]
                else:
                    date_obj = datetime.strptime(line, '%Y-%m-%d')
                    year, week, _ = date_obj.isocalendar()
                    current_period = f"{year}-W{week:02d}"
                continue
                
            # Match numstat line
            parts = line.split('\t')
            if len(parts) >= 3 and current_period:
                added, removed, filepath = parts[0], parts[1], parts[2]
                
                if added.isdigit() and removed.isdigit() and is_handwritten_code(filepath):
                    period_data[current_period]['added'] += int(added)
                    period_data[current_period]['removed'] += int(removed)

        return period_data
    except Exception as e:
        return None

def print_histogram(data_dict, title):
    print(f"\n{'=' * 95}")
    print(f"{title}")
    print(f"{'=' * 95}")
    
    if not data_dict:
        print("No data available.")
        return

    max_val = max(abs(d['added'] - d['removed']) for d in data_dict.values())
    max_val = max(max_val, 1) 
    max_bar_length = 30
    
    print(f"{'Period':<10} | {'Readable Date':<13} | {'Added':>9} | {'Removed':>9} | {'Net Growth':>10} | Graph (Net Growth)")
    print("-" * 95)
    for period in sorted(data_dict.keys()):
        data = data_dict[period]
        added = data['added']
        removed = data['removed']
        net = added - removed
        
        try:
            if 'W' in period:
                y, w = period.split('-W')
                d = datetime.fromisocalendar(int(y), int(w), 1)
                readable = d.strftime('%b %d, %Y')
            else:
                y, m = period.split('-')
                d = datetime(int(y), int(m), 1)
                readable = d.strftime('%b %Y')
        except Exception:
            readable = ""
            
        bar_length = int((abs(net) / max_val) * max_bar_length)
        bar_char = '█' if net >= 0 else '▒'
        bar = bar_char * bar_length
        if net < 0:
            bar = f"({bar})"
            
        print(f"{period:<10} | {readable:<13} | {added:>9,} | {removed:>9,} | {net:>10,} | {bar}")

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    written_lines = 0
    library_lines = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Prevent traversal of known huge useless directories
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.mypy_cache', '.claude', '.agents'}]
        
        for file in files:
            filepath = os.path.join(root, file)
            # Use relative path for fair comparison with git
            rel_path = os.path.relpath(filepath, root_dir).replace('\\', '/')
            
            ext = os.path.splitext(file)[1].lower()
            
            # We still only count code extensions overall for the top summary
            if ext in CODE_EXTENSIONS:
                lines = count_lines_in_file(filepath)
                
                # Use the exact same shared logic for what counts as handwritten
                if is_handwritten_code(rel_path):
                    written_lines += lines
                elif any(lib in rel_path for lib in LIBRARY_SUBSTRINGS):
                    library_lines += lines
                    
    print("=" * 95)
    print("CURRENT WORKSPACE: LINES OF CODE SUMMARY")
    print("=" * 95)
    print(f"Written LOC:             {written_lines:,}")
    print(f"Library/Shipped LOC:     {library_lines:,}")
    print(f"Total LOC:               {written_lines + library_lines:,}")
    print("(Note: These counts use the EXACT same filters as the historical log below)")
    
    history_month = get_historical_loc(grouping='month')
    if history_month:
        print_histogram(history_month, "HISTORICAL: MONTH-WISE WRITTEN CODE (via Git)")

    history_week = get_historical_loc(grouping='week')
    if history_week:
        print_histogram(history_week, "HISTORICAL: WEEK-WISE WRITTEN CODE (via Git)")

if __name__ == "__main__":
    main()
