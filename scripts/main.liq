log.stdout := true

# === Playlists and fallback setup ===
default = single("/liqfolder/jinglemix.ogg")      # Fallback track
day = playlist("/liqfolder/mixes.m3u")     # Day (6h–22h): mixes
night = playlist("/liqfolder/ytauto.m3u")  # Night (22h–6h): downloads (ytauto)
jingles = playlist("/liqfolder/jingles.m3u")      # Jingles playlist
clock = single("/liqfolder/jinglemix.ogg")        # Clock jingle for top-of-hour
gosp3 = playlist("/liqfolder/gosp3.m3u")
satmix = playlist("/liqfolder/satmix.m3u")

# Daily GLC News at 5:00 PM Pacific. Liquidsoap TZ is America/New_York.
# Pacific and Eastern stay 3 hours apart year-round, so 5 PM PT is always 8 PM ET.
# Fallible: if the MP3 is missing, this source is not ready and music stays on.
news_path = "/liqfolder/glconnect/static/audio/final_news_broadcast.mp3"
news = once(single(news_path))

# === Time-based switching between day and night playlists ===
music = switch([
  ({ 0w }, gosp3),
  ({ 6w }, satmix),
  ({ 7w }, satmix),
  ({ 6h-22h }, day),    # Day: mixes.m3u
  ({ 22h-6h }, night),  # Night: ytauto.m3u (downloads)
  ({ true }, night)
])
music = fallback([music, default])  # Fallback to default if playlists fail

# === Add jingles randomly (1 jingle every 2 songs) ===
music = random(weights=[1, 2], [jingles, music])

# === Add top-of-the-hour clock jingle (skipped during the news window) ===
music = add([music, switch([({ 0m0s }, clock)])])

# 8:00–8:30 PM Eastern = 5:00–5:30 PM Pacific, every day.
# track_sensitive=false starts news on time. Missing MP3 leaves this
# switch unready, so fallback keeps the regular music playlists.
radio = fallback(track_sensitive=false, [
  switch(track_sensitive=false, [({ 20h0m-20h30m }, news)]),
  music
])

# === Make radio stream safe and create final fallback ===
radio = fallback([radio, default])
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