# Fix YouTube "Sign in to confirm you're not a bot"

When the admin YouTube download fails with **Sign in to confirm you're not a bot**, YouTube is blocking the server. Use a **cookies file** so yt-dlp can authenticate like a browser.

## 1. Export cookies (on your computer)

1. **Install a cookies export extension** in Chrome/Firefox, e.g.:
   - [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome)
   - Or use [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox)

2. **Open YouTube** in that browser and make sure you're **logged in**.

3. **Export cookies** for `youtube.com` in **Netscape format** (cookies.txt). Save as `ytdlp_cookies.txt`.

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
