# CI/CD Pipeline – Step-by-Step

This doc describes how a deploy pipeline would work for this app: **push from local → remote pulls, rebuilds Docker, and restarts** without you SSHing in to deploy.

---

## 1. Overview

| Step | Where | What happens |
|------|--------|--------------|
| 1 | Your Mac | You code, commit, and `git push origin enhancements` |
| 2 | GitHub | Receives the push and runs the workflow (e.g. GitHub Actions) |
| 3 | Workflow | Optionally runs tests/lint, then runs the deploy job |
| 4 | Deploy job | SSHs into your server and runs: `git pull` (from `enhancements`) → `docker compose build` → `docker compose up -d` |
| 5 | Server | App runs from the new code; no manual SSH needed for deploy |

**Paths:**
- **Local (development):** project directory is **music-1** (e.g. `.../music-1` on your Mac).
- **Server (Linux):** app lives at **~/music** (e.g. `/home/nididier/music`). The pipeline runs `git pull` and `docker compose` there.

**Note:** The pipeline is set up for the **enhancements** branch (your current production branch). If you later use `main` again, change the workflow trigger and the `git reset` branch in `.github/workflows/deploy.yml`.

---

## 2. Step-by-Step Flow

### Step 1 – You push (local)

- You work in **music-1** on your Mac (e.g. `/Applications/untitled folder/music-1`).
- You commit and push:
  ```bash
  git add .
  git commit -m "Your message"
  git push origin enhancements
  ```

### Step 2 – GitHub runs the workflow

- Trigger: push to **enhancements** (your current production branch).
- The workflow file is `.github/workflows/deploy.yml`.
- GitHub Actions starts a runner and runs the jobs defined there.

### Step 3 – Workflow: optional CI (tests/lint)

- If you add tests or lint:
  - Job checks out the repo, installs deps, runs tests/lint.
  - If this job fails, the pipeline can stop and **not** deploy (recommended).

### Step 4 – Workflow: deploy job (CD)

- The deploy job:
  1. Checks out the repo (so it has the latest code; optional if you only need SSH).
  2. Sets up SSH (using a secret: private key, and known_hosts for the server).
  3. SSHs into the server (e.g. `nididier@167.172.224.239`).
  4. Runs on the server:
     ```bash
     cd /home/nididier/music
     git fetch origin && git reset --hard origin/enhancements
     docker compose build app
     docker compose up -d
     ```
- Replace `app` with the service name(s) you want to rebuild (e.g. `app nginx` if nginx is built from this repo).

### Step 5 – Server state after deploy

- Repo on server is up to date with **enhancements**.
- `myapp:latest` (and any other built images) are rebuilt from the new code.
- Containers are recreated with `docker compose up -d`.
- You do **not** need to SSH to run these commands; the pipeline does it.

---

## 3. What you need to set up

1. **GitHub repo** – Code pushed to `main` (or your production branch).
2. **Workflow file** – `.github/workflows/deploy.yml` (example is in this repo).
3. **Secrets in GitHub** (Settings → Secrets and variables → Actions):
   - `SSH_PRIVATE_KEY` – Private key that can SSH into the server as `nididier`. (Edit the workflow file if your host/username differ.)
4. **Server** – Same as now:
   - Git clone at **~/music** (e.g. `/home/nididier/music`) — this is where you pull and run Docker.
   - Docker and Docker Compose installed.
   - The SSH key’s public half in `~/.ssh/authorized_keys` for the deploy user.
   - **Passwordless sudo for udev** (so the pipeline can run udev cleanup): on the server, run once: `sudo bash scripts/setup-passwordless-sudo-udev.sh` (from inside `~/music` after pull). This creates `/etc/sudoers.d/nididier-deploy-udev` so the deploy user can run the two udev commands without a password.

---

## 4. Order of commands on the server (what the pipeline runs)

The pipeline matches the manual full-deploy order (so app runs the same as when you deploy by hand):

```text
1. cd ~/music
2. git fetch origin && git reset --hard origin/enhancements
3. docker compose down
4. udev cleanup (sudo find /run/udev/data ..., systemctl start systemd-udevd; errors ignored)
5. docker system prune -a -f
6. docker compose build
7. docker compose up -d
8. (wait for app and nginx→app)
```

- **Step 2:** Update code from the **enhancements** branch.
- **Steps 3–5:** Clean slate (down, udev, prune), like manual deploy.
- **Step 6:** Rebuild all images (app, nginx, fastapi).
- **Step 7:** Start all containers.
- **Udev (step 4):** The pipeline runs the udev commands without a password. **One-time setup on the server:** run `sudo bash scripts/setup-passwordless-sudo-udev.sh` (from the repo) to allow the deploy user to run those two sudo commands without a password. See `scripts/setup-passwordless-sudo-udev.sh`.

**When to do more:**
- **You changed nginx or FastAPI code:** SSH in and run `docker compose build nginx` (or `fastapi`) then `docker compose up -d`, or add a second workflow that builds all images (e.g. on a different branch or manual trigger).
- **Disk full / clean slate:** Run manually on the server: `docker compose down`, `docker system prune -a -f`, then pull and build the images you need and `docker compose up -d`.
- **Udev:** The pipeline runs udev cleanup automatically. If you see sudo errors in the deploy log, run the one-time setup on the server: `sudo bash scripts/setup-passwordless-sudo-udev.sh`.

---

## 4a. Avoiding conflicts between local and server

- **Single source of truth:** The server is always reset to `origin/enhancements` on each deploy (`git reset --hard origin/enhancements`). So the code that runs on the server is exactly what’s in the repo for that branch. Any edits made directly on the server are overwritten by the next deploy.
- **Work only from local (and push):** Do all code changes locally, commit, and push. Don’t rely on uncommitted or server-only changes; they will be lost on the next deploy.
- **Pull before you push:** On your Mac, run `git pull origin enhancements` (or pull and merge) before pushing, so you don’t push an outdated branch and overwrite others’ work.
- **What the pipeline checks:** After reset, the workflow runs `git status --short` and prints the deployed commit (`git log -1 --oneline`). In the Actions log you can confirm the tree is clean and which commit was deployed, so build and server stay in sync.

---

## 4b. Manual full deploy on server (your sequence)

If you run a full clean deploy by hand:

```text
1. cd /home/nididier/music
2. docker compose down
3. docker system prune -a -f
4. sudo find /run/udev/data -type f -delete    # errors ignored
5. sudo systemctl start systemd-udevd           # errors ignored
6. git fetch origin && git reset --hard origin/enhancements
7. docker build -t myapp:latest .
8. docker build -t fastapi:latest -f Dockerfile.uvi .
9. docker build -t custom-nginx -f Dockerfile.nginx .   # optional; compose will build nginx if needed
10. docker compose up -d
11. (optional) Wait for app to be ready — see below (avoids 502).
```

**Why you can get 502 after step 10:**  
`depends_on: app` only waits for the **app container** to start. Flask inside the app container takes longer to open port 5000 (DB init, TTS, etc.; the app has `start_period: 60s`). Nginx can receive requests and proxy to `myapp:5000` before the app is listening → connection refused → **502 Bad Gateway**.

**Fix: wait for the app before trusting the site**

After `docker compose up -d`, run (on the server):

```bash
until curl -sf http://localhost:5000/health; do echo "waiting for app..."; sleep 5; done; echo "App is up."
```

Or wait ~60–90 seconds before hitting the site. Once the app is up, 502 from “not ready yet” should stop.

**Also ensure:** The repo has the latest `docker-compose.yml` (step 6) so the **app** service has `networks: app_network: aliases: [myapp]`. Without that, nginx cannot resolve `myapp` and will 502.

---

## 5. When you still use SSH

- **Deploy:** No SSH needed; the pipeline does it.
- **Logs:** `ssh ... 'cd ~/music && docker compose logs -f app'`
- **Debug / one-off:** Restart a service, edit config, inspect DB, etc.

---

## 6. File that defines the pipeline

- The pipeline behaviour is defined in:
  - **`.github/workflows/deploy.yml`**
- That file contains the exact steps above: trigger on push → (optional test job) → deploy job that SSHs and runs the commands in section 4.

---

## 7. Summary

| Question | Answer |
|----------|--------|
| What runs the pipeline? | GitHub Actions (when you push to **enhancements**). |
| What does the pipeline do on the server? | `cd` to app dir → `git pull` (or fetch/reset) → `docker compose build app` → `docker compose up -d`. |
| Do I need to SSH to deploy? | No. Only for logs and manual fixes. |
| Where is the workflow defined? | `.github/workflows/deploy.yml`. |

---

## 8. Customizing

- **Branch:** The workflow uses **enhancements**. To use `main` or another branch, change `branches: [enhancements]` and the `git reset --hard origin/...` line in the workflow.
- **Server path:** The workflow uses `cd /home/nididier/music` (i.e. **~/music** on the server). If your app lives elsewhere, edit the `script` in the deploy step.
- **Services to build:** The example builds only `app`. To rebuild nginx too: `docker compose build app nginx`.
- **Secrets:** Add `SSH_PRIVATE_KEY` in GitHub (Settings → Secrets and variables → Actions). Edit the workflow file to change host, username, or app path.
