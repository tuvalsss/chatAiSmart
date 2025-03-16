import os
import json
import time

def index_project():
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    index_file = os.path.join(logs_dir, "project_index.json")
    
    project_structure = {}
    
    for root, dirs, files in os.walk("."):
        relative_root = os.path.relpath(root, ".")
        if relative_root == ".":
            relative_root = "root"
        project_structure[relative_root] = files
    
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(project_structure, f, indent=4)
    
    print("✅ Project indexing completed. Check logs/project_index.json for details.")

if __name__ == "__main__":
    index_project()
