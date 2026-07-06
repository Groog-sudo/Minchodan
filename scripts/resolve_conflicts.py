import os
from pathlib import Path

def resolve_conflict_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Skipping {filepath}: {e}")
        return

    new_lines = []
    in_conflict = False
    in_head = False
    in_dev = False

    has_conflict = False

    for line in lines:
        if line.startswith("<<<<<<< HEAD"):
            has_conflict = True
            in_conflict = True
            in_head = True
            in_dev = False
            continue
        elif line.startswith("======="):
            if in_conflict:
                in_head = False
                in_dev = True
                continue
        elif line.startswith(">>>>>>> dev"):
            if in_conflict:
                in_conflict = False
                in_head = False
                in_dev = False
                continue
        
        if in_conflict:
            if in_dev:
                new_lines.append(line)
            # if in_head, we discard
        else:
            new_lines.append(line)
            
    if has_conflict:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"Resolved conflicts in {filepath}")

def main():
    root_dir = Path(r"c:\Dev_task\workspace\Project\finally_project\AI_GilDang\Minchodan")
    exclude_dirs = {".git", "node_modules", "venv", "__pycache__"}
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for f in filenames:
            if f == "package-lock.json":
                continue
            if not f.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".md")):
                continue
            resolve_conflict_file(os.path.join(dirpath, f))

if __name__ == "__main__":
    main()
