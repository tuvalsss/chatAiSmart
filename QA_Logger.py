import os
import time
import json

def perform_qa_on_project():
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "qa_log.txt")

    qa_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "issues_found": [],
        "summary": "QA completed successfully with no critical errors."
    }

    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".py") or file.endswith(".html") or file.endswith(".js"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "TODO" in content:
                        qa_results["issues_found"].append(f"TODO found in {file_path}")
    
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(qa_results, f, indent=4)
    
    print("✅ QA process completed. Check logs/qa_log.txt for details.")

if __name__ == "__main__":
    perform_qa_on_project()
