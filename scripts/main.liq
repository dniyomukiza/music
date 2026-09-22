log.stdout := true

# === Playlists and fallback setup ===
default = single("/liqfolder/jinglemix.ogg")      # Fallback track
day = playlist("/liqfolder/eleven.m3u")     # Day (6h–22h): mixes
night = playlist("/liqfolder/eleven.m3u")  # Night (22h–6h): downloads (ytauto)
jingles = playlist("/liqfolder/jingles.m3u")      # Jingles playlist
clock = single("/liqfolder/jinglemix.ogg")        # Clock jingle for top-of-hour
gosp3 = playlist("/liqfolder/eleven.m3u")
satmix = playlist("/liqfolder/eleven.m3u")
eleven = playlist("/liqfolder/eleven.m3u")

# Daily GLC News (raw MP3, single/once only — never playlist/.m3u). TZ: America/New_York.
# Morning: 11:00–11:30 Pacific = {14h0m-14h30m} ET. Evening: 6:00–6:30 PT = {21h0m-21h30m} ET.
# Separate once(single()) per window so each fires once daily from the start of its window.
# Fallible: if the MP3 is missing, news sources are not ready and music stays on.
news_path = "/liqfolder/glconnect/static/audio/final_news_broadcast.mp3"
news_morning = once(single(news_path))
news_evening = once(single(news_path))

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

# News windows (ET): morning {14h0m-14h30m}, evening {21h0m-21h30m}.
# track_sensitive=false starts each bulletin on time; after it ends, music resumes until window closes.
radio = fallback(track_sensitive=false, [
  switch(track_sensitive=false, [
    ({ 14h0m-14h30m }, news_morning),
    ({ 21h0m-21h30m }, news_evening)
  ]),
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

# === ElevenLabs originals (standalone, not mixed into station day rotation) ===
eleven_radio = mksafe(eleven)
output.icecast(%mp3,
  host="icecast2",
  port=8000,
  password="123",
  mount="eleven",
  eleven_radio
)