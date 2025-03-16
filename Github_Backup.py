import os
import subprocess
import time

def backup_github_repo():
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "github_backup_log.txt")
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = f"backup_{timestamp}"

    os.makedirs(backup_dir, exist_ok=True)
    
    result = subprocess.run(["git", "clone", "--mirror", os.getenv("GITHUB_REPO_URL"), backup_dir], capture_output=True, text=True)
    
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(result.stdout + "\n" + result.stderr)
    
    print(f"✅ GitHub backup completed. Backup stored in {backup_dir}")

if __name__ == "__main__":
    backup_github_repo()
