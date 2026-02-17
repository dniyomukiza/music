# Fix YouTube "Sign in to confirm you're not a bot"

When the admin YouTube download fails with **Sign in to confirm you're not a bot**, YouTube is blocking the server. Use a **cookies file** so yt-dlp can authenticate like a browser.

## 1. Export cookies (on your computer)

**Easiest: use yt-dlp (no browser extension needed)**

On a machine where you're logged into YouTube in Chrome (or Firefox), run:

```bash
yt-dlp --cookies-from-browser chrome --cookies ytdlp_cookies.txt --skip-download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

(Some yt-dlp versions require a URL; `--skip-download` avoids actually downloading. This reads Chrome's cookies and writes them to `ytdlp_cookies.txt` in **Mozilla/Netscape format**.) Use that file on the server.

- **Firefox:** `yt-dlp --cookies-from-browser firefox --cookies ytdlp_cookies.txt`
- **Chrome via Flatpak (Linux):** `yt-dlp --cookies-from-browser "chrome:~/.var/app/com.google.Chrome/" --cookies ytdlp_cookies.txt`

*Note: this exports cookies for all sites in that browser profile. Keep the file private and only copy it to your server.*

**Alternative: browser extension**

1. Install [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome) or [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox).  
2. Open **youtube.com** while logged in, then export cookies for `youtube.com` in **Netscape format**. Save as `ytdlp_cookies.txt`.

**Cookie file format (important for Linux server)**

- The file must be **Mozilla/Netscape format**. The first line must be either `# HTTP Cookie File` or `# Netscape HTTP Cookie File`.
- Use **LF** (`\n`) line endings for Linux/macOS. **CRLF** (Windows) can cause `HTTP Error 400: Bad Request` when using `--cookies` on a Linux server. If you created the file on Windows, convert to LF (e.g. `sed -i 's/\r$//' ytdlp_cookies.txt` on the server, or save as “Unix” in your editor).

## 2. Put the file on the Linux server

From your computer (replace `user@your-server` and path):

```bash
scp ytdlp_cookies.txt user@your-server:/path/to/music-1/ytdlp_cookies.txt
```

So the file is in the **project root** on the server (same folder as `docker-compose.yml`).

## 3. Use it in the app

- **Docker:** The repo is already set up: `YTDLP_COOKIES_FILE=/usr/src/appdir/ytdlp_cookies.txt` is in `docker-compose.yml`, and the project root is mounted, so `./ytdlp_cookies.txt` on the server is visible at that path in the container. Restart the app service:

  ```bash
  docker compose restart app
  ```

- **No Docker:** Set the env var before running the app, e.g.:

  ```bash
  export YTDLP_COOKIES_FILE=/path/to/music-1/ytdlp_cookies.txt
  ```

Then run the admin YouTube download again; it should use the cookies and avoid the bot message.

## Security

- `ytdlp_cookies.txt` is in `.gitignore` — do not commit it.
- The file gives access to your YouTube account; keep it only on the server and restrict file permissions: `chmod 600 ytdlp_cookies.txt`.

## Re-export when it stops working

YouTube cookies expire. If downloads start failing again with the same error, export a fresh `ytdlp_cookies.txt` from your browser and replace the file on the server, then restart the app.

---

## Troubleshooting: "Sign in to confirm you're not a bot" still appears

1. **Confirm the file exists on the server** (in the same directory as `docker-compose.yml`):
   ```bash
   ls -la /path/to/music-1/ytdlp_cookies.txt
   ```
   If you use Docker, this must be the directory that is mounted into the container (the one where you run `docker compose`).

2. **Confirm the container sees the file and env:**
   ```bash
   docker compose exec app ls -la /usr/src/appdir/ytdlp_cookies.txt
   docker compose exec app env | grep YTDLP
   ```
   You should see the file and `YTDLP_COOKIES_FILE=/usr/src/appdir/ytdlp_cookies.txt`. If the file is missing, the project directory on the host is wrong or the volume mount is different.

3. **Check app logs when you start a download:**  
   The pipeline now logs either:
   - `Using cookies file: /usr/src/appdir/ytdlp_cookies.txt` → cookies are used.
   - `YTDLP_COOKIES_FILE is set but file not found: ...` → path is wrong or file isn’t in the mounted directory.
   - `No YTDLP_COOKIES_FILE set` → env var not set; restart after adding it to `docker-compose.yml`.

4. **Restart the app** after adding or changing the cookies file or env:
   ```bash
   docker compose restart app
   ```

5. **Cookie format:** The file must be **Netscape format** (first line `# HTTP Cookie File` or `# Netscape HTTP Cookie File`). Use **LF** line endings on the server—CRLF (Windows) can cause **HTTP 400**. Convert: `sed -i 's/\r$//' ytdlp_cookies.txt`. Re-export from the browser extension and ensure you chose Netscape/cookies.txt format for youtube.com (one cookie per line, tab-separated fields). Re-export from the browser extension and ensure you chose “Netscape” or “cookies.txt” format for `youtube.com`.
