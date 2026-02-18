log.stdout := true

# === Playlists and fallback setup ===
default = single("/liqfolder/jinglemix.ogg")      # Fallback track
day = playlist("/liqfolder/ytauto.m3u")   # Day: downloads (ytauto, at project root)
night = playlist("/liqfolder/mixes.m3u")   # Night playlist (22h–6h, project root)
jingles = playlist("/liqfolder/jingles.m3u")      # Jingles playlist
clock = single("/liqfolder/jinglemix.ogg")        # Clock jingle for top-of-hour
gosp3 = playlist("/liqfolder/gosp3.m3u")
satmix = playlist("/liqfolder/satmix.m3u")
# === Time-based switching between day and night playlists ===
radio = switch([
  ({ 0w }, gosp3),
  ({ 6w }, satmix),
  ({ 7w }, satmix),
  ({ 6h-22h }, day),    # Day: ytauto.m3u (downloads)
  ({ 22h-6h }, night),  # Night: mixes.m3u
  ({ true }, night)  
])
radio = fallback([radio, default])  # Fallback to default if playlists fail

# === Add jingles randomly (1 jingle every 2 songs) ===
radio = random(weights=[1, 2], [jingles, radio])

# === Add top-of-the-hour clock jingle ===
radio = add([radio, switch([({ 0m0s }, clock)])])

# === Make radio stream safe and create final fallback ===
radio = mksafe(radio)

# Uncomment this if you have a live input stream
# live_show = input.harbor("http://localhost:8000/station")

full = fallback(track_sensitive=false, [
  # live_show,
  radio
])

# === Output MAIN station in MP3 ===
output.icecast(%mp3,
  host="icecast2",
  port=8000,
  password="123",
  mount="station",
  full
)

# === Gosp3 Stream Setup (MP3) ===
gosp3_radio = mksafe(gosp3)
output.icecast(%mp3,
  host="icecast2",
  port=8000,
  password="123",
  mount="gosp3",
  gosp3_radio
)

# === Saturday stream ===
sat_radio = mksafe(satmix)
output.icecast(%mp3,
  host="icecast2",
  port=8000,
  password="123",
  mount="satmix",
  sat_radio
)