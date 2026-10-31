# Setup on Windows (WSL) or Google Cloud Shell

The labs are Bash scripts, so they run anywhere with a Linux shell. Pick one:

| | Windows + WSL | Google Cloud Shell |
| --- | --- | --- |
| Install | ~20 min, once | Nothing: gcloud, git, Python, Node, Terraform are there |
| Antigravity CLI (agent steps) | Install inside WSL | May not be available; use the fallback scripts or run agent steps on your laptop |
| `adk web` (Labs 1–2) | `localhost:8000` in your Windows browser | Web Preview on port 8000 |
| Watch out for | Work in `~`, not `/mnt/c`; Windows line endings | Idle sessions disconnect; exported variables are lost |

Finish either path with `./scripts/check-env.sh`: it checks every tool and version and changes nothing.

## Windows: WSL (Ubuntu)

1. **Install WSL** — PowerShell as Administrator, then restart and create your Linux user:

   ```powershell
   wsl --install -d Ubuntu-24.04
   ```

2. **Base tools** — in the Ubuntu terminal (Ubuntu 24.04 ships Python 3.12):

   ```bash
   sudo apt update && sudo apt install -y python3 python3-venv python3-pip git curl gnupg
   ```

3. **gcloud CLI** (Google's apt repository):

   ```bash
   curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
   echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
     | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
   sudo apt update && sudo apt install -y google-cloud-cli
   ```

4. **Node 22.20+** (only for `npx skills`), with nvm:

   ```bash
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
   source ~/.bashrc && nvm install --lts && node -v
   ```

5. **Terraform** (only for the Lab 3–4 agent steps): follow the Ubuntu/Debian steps at
   developer.hashicorp.com/terraform/install.

6. **Antigravity CLI**: install its Linux version inside WSL (antigravity.google), then `./scripts/00-skills.sh`.
   Without it, use each lab's fallback script.

7. **Log in** — a browser opens on Windows; if not, add `--no-launch-browser` and paste the code back:

   ```bash
   gcloud auth login
   gcloud auth application-default login     # for adk web
   gcloud config set project <your-project-id>
   ```

8. **Clone the repo into your Linux home** (not `/mnt/c/...`: slower, and file modes break):

   ```bash
   cd ~ && git clone https://github.com/ronaldyuwandika/autonomous-sre-agent-workshop.git
   cd autonomous-sre-agent-workshop && ./scripts/check-env.sh
   ```

   Clone inside WSL, not with Git for Windows: Windows line endings break the scripts
   (`/usr/bin/env: 'bash\r'`). Fix: `sed -i 's/\r$//' scripts/*.sh`. Not executable: `chmod +x scripts/*.sh`.

`adk web` (Lab 1) serves on `localhost:8000`; open that in your Windows browser.

## Google Cloud Shell

1. **Open it** — console.cloud.google.com → the **Activate Cloud Shell** button (`>_`) at the top right.
   Click **Open Editor** if you want a file view.

2. **Set the project** (Cloud Shell is already logged in as you):

   ```bash
   gcloud config set project <your-project-id>
   ```

3. **Clone the repo**:

   ```bash
   git clone https://github.com/ronaldyuwandika/autonomous-sre-agent-workshop.git
   cd autonomous-sre-agent-workshop && ./scripts/check-env.sh
   ```

4. **Node**, only if `check-env.sh` says it's too old: `nvm install --lts`.

5. **`adk web` in Lab 1** — bind to all interfaces and allow the Cloud Shell preview origin, then
   **Web Preview → Change port → 8000**:

   ```bash
   adk web --host 0.0.0.0 --port 8000 --allow_origins "regex:https://.*\.cloudshell\.dev"
   ```

6. **Credentials** — the client libraries in Cloud Shell use your login. If `adk web` reports no credentials,
   run `gcloud auth application-default login`.

Good to know:

- Cloud Shell disconnects when idle and `export`s are lost on reconnect. Re-export what you set
  (`SLACK_APPROVERS`, `SMTP_*`, `EMAIL_TO`, `AUTONOMY`) before re-running `04-deploy-agent.sh`.
  Files in your home folder persist.
- Agent steps need Antigravity CLI. If you can't install it in Cloud Shell, run them on your laptop or
  use the fallback script named in each lab.
- Everything else, including the Slack setup and `scripts/incidents.sh`, works the same.
