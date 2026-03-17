# Fix YouTube "Sign in to confirm you're not a bot"

When the admin YouTube download fails with **Sign in to confirm you're not a bot**, YouTube is blocking the server. Use a **cookies file** so yt-dlp can authenticate like a browser.

**Typical setup:** Export cookies on your **Mac** (local), then copy the file to the **Linux server** where the app runs.

## Why "Sign in to confirm you're not a bot" can persist even with cookies

1. **Cookie rotation:** YouTube rotates account cookies when you have YouTube open in the browser. If you export with `--cookies-from-browser` from a profile where YouTube is open (or was open recently), those cookies may already be invalid by the time the server uses them. So the export can "look" correct but still fail.
2. **Server not using the file:** The app only uses cookies if `YTDLP_COOKIES_FILE` is set and the file exists at that path **inside the container**. If the file is missing on the server or the path is wrong, you'll still see the bot error.

**Best approach for reliable cookies:** Use a **browser extension** and avoid re-opening YouTube in that session after exporting (or use incognito and export with the extension, then close incognito). See "Export cookies (reliable)" below.

## 1. Export cookies (on your Mac)

**Option A – Reliable: browser extension (recommended for YouTube)**

1. Install **Get cookies.txt LOCALLY** (Chrome) or **cookies.txt** (Firefox). Do not use "Get cookies.txt" without LOCALLY—reported as malware.
2. Open **youtube.com** in the profile where you're logged in (or in an incognito window where you just logged in).
3. Use the extension to export cookies for the current site in **Netscape** format. Save as e.g. `ytdlp_cookiesfull.txt`.
4. **Right after exporting:** close YouTube tabs (or close incognito) so YouTube doesn’t rotate the cookies. Copy the file to the server and run the download soon.

**Option B – yt-dlp from browser (can fail due to rotation)**

On a machine where you're logged into YouTube in Chrome (or Firefox), run:

```bash
yt-dlp --cookies-from-browser "chrome:Profile 10" --cookies ytdlp_cookiesfull.txt --skip-download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

- **Default Chrome:** `--cookies-from-browser chrome`
- **Firefox:** `--cookies-from-browser firefox`
- **Chrome via Flatpak (Linux):** `--cookies-from-browser "chrome:~/.var/app/com.google.Chrome/"`
- **Specific profile (e.g. Profile 10):** `--cookies-from-browser "chrome:Profile 10"` — get name from `chrome://version` in that profile.

If you still get the bot error after copying to the server, YouTube likely rotated the cookies. Use Option A (extension) and export right before copying, or try the incognito method in the troubleshooting section.

*Note: Option B exports cookies for **all sites** in that profile. Keep the file private.*

**Cookie file format (important for Linux server)**

- The file must be **Mozilla/Netscape format**. The first line must be either `# HTTP Cookie File` or `# Netscape HTTP Cookie File`.
- Use **LF** (`\n`) line endings for Linux/macOS. **CRLF** (Windows) can cause `HTTP Error 400: Bad Request` when using `--cookies` on a Linux server. If you created the file on Windows, convert to LF (e.g. `sed -i 's/\r$//' ytdlp_cookies.txt` on the server, or save as “Unix” in your editor).

## 2. Copy the file to the Linux server

From your Mac (replace `user@your-server` and path with your Linux host):

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

1. **Confirm the file exists on the server** (in the same directory as `docker-compose.yml`). The app uses the file set in `YTDLP_COOKIES_FILE` (e.g. `ytdlp_cookiesfull.txt` or `ytdlp_cookies.txt`):
   ```bash
   ls -la /path/to/music-1/ytdlp_cookiesfull.txt
   ```
   If you use Docker, this must be the directory that is mounted into the container (the one where you run `docker compose`).

2. **Confirm the container sees the file and env:**
   ```bash
   docker compose exec app ls -la /usr/src/appdir/ytdlp_cookiesfull.txt
   docker compose exec app env | grep YTDLP
   ```
   You should see the file and `YTDLP_COOKIES_FILE=/usr/src/appdir/ytdlp_cookiesfull.txt` (or whatever name you use). If the file is missing, the project directory on the host is wrong or the volume mount is different.

3. **Check app logs when you start a download:**  
   The pipeline now logs either:
   - `Using cookies file: /usr/src/appdir/ytdlp_cookies.txt` → cookies are used.
   - `YTDLP_COOKIES_FILE is set but file not found: ...` → path is wrong or file isn’t in the mounted directory.
   - `No YTDLP_COOKIES_FILE set` → env var not set; restart after adding it to `docker-compose.yml`.

4. **Restart the app** after adding or changing the cookies file or env:
   ```bash
   docker compose restart app
   ```

5. **Cookie format:** The file must be **Netscape format** (first line `# HTTP Cookie File` or `# Netscape HTTP Cookie File`). Use **LF** line endings on the server—CRLF (Windows) can cause **HTTP 400**. Convert: `sed -i 's/\r$//' ytdlp_cookies.txt`. Re-export from the browser extension and ensure you chose Netscape/cookies.txt format for youtube.com (one cookie per line, tab-separated fields). Re-export from the browser extension and ensure you chose “Netscape” or “cookies.txt” format for youtube.com.

6. **Cookie rotation (still failing with valid file):** YouTube rotates cookies when you use the site. If you exported with `--cookies-from-browser` while (or shortly after) having YouTube open, try instead:
   - **Extension method:** Install "Get cookies.txt LOCALLY" in Chrome, open youtube.com (logged in), export for this site in Netscape format, then **close all YouTube tabs**, copy the file to the server and run the download soon.
   - **Incognito + extension:** Open an incognito window, log into YouTube only there, export cookies with the extension, then close incognito (so that session is never opened again). Use that file on the server. Do not use `--cookies-from-browser` for incognito—it cannot see incognito cookies; you must use the extension.

---

## Quick checklist when the bot error persists

- [ ] On the **server**, file exists where the app expects it:  
  `docker compose exec app ls -la /usr/src/appdir/ytdlp_cookiesfull.txt`  
  and `docker compose exec app env | grep YTDLP` shows `YTDLP_COOKIES_FILE=/usr/src/appdir/ytdlp_cookiesfull.txt`.
- [ ] When you start a download, app logs show **"Using cookies file: /usr/src/appdir/ytdlp_cookiesfull.txt"** (not "file not found" or "No YTDLP_COOKIES_FILE set").
- [ ] Cookie file is **Netscape** format and **LF** line endings on the server.
- [ ] Re-exported cookies using the **browser extension** (Get cookies.txt LOCALLY), then closed YouTube tabs, copied the new file to the server, and ran the download soon after.
- [ ] Restarted the app after updating the cookies file: `docker compose restart app`.
