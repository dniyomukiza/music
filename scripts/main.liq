log.stdout := true

# === Playlists and fallback setup ===
default = single("/liqfolder/jinglemix.ogg")      # Fallback track
night = playlist("/liqfolder/mixes.m3u")            # Day playlist
day= playlist("/liqfolder/afro.m3u")           # Night playlist
jingles = playlist("/liqfolder/jingles.m3u")      # Jingles playlist
clock = single("/liqfolder/jinglemix.ogg")        # Clock jingle for top-of-hour
gosp3 = playlist("/liqfolder/gosp3.m3u")
# === Time-based switching between day and night playlists ===
radio = switch([
  ({1w and true}, gosp3),  
  ({ 6h-22h }, day),   # 6AM to 10PM = day
  ({ 22h-6h }, night)  # 10PM to 6AM = night
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
