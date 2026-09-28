log.stdout := true

# === Playlists and fallback setup ===
default = single("/liqfolder/jinglemix.ogg")      # Fallback track
# Rotate needs two plain playlists. A switch/fallback child is treated as one
# continuous source, so jingles never get a turn.
songs = playlist(id="eleven_songs", reload_mode="watch", mode="normal", "/liqfolder/eleven.m3u")
jingles = fallback(track_sensitive=true, [
  playlist(id="radio_jingles", reload_mode="watch", mode="normal", "/liqfolder/jingles.m3u"),
  single("/liqfolder/jingle.mp3"),
  single("/liqfolder/jinglemix.ogg")
])
clock = single("/liqfolder/jinglemix.ogg")        # Clock jingle for top-of-hour
gosp3 = playlist("/liqfolder/eleven.m3u")
satmix = playlist("/liqfolder/eleven.m3u")
eleven = playlist("/liqfolder/eleven.m3u")

# Daily GLC News (raw MP3, request.dynamic only — never playlist/.m3u).
# Container TZ is America/Los_Angeles: 11:00–11:30 AM and 6:00–6:30 PM Pacific.
# predicate.once({window}) re-arms when the window closes, so each calendar day gets both slots
# without restarting liquidsoap (source once() is once-per-process-lifetime and must not be used).
# Fallible: if final_news_broadcast.mp3 is missing, the slot is skipped and jingles/songs stay on.
# request.dynamic resolves the file when the window opens, so a replaced MP3 is today's bulletin.
news_path = "/liqfolder/glconnect/static/audio/final_news_broadcast.mp3"
news_morning = request.dynamic(id="glc_news_morning", {request.create(news_path)})
news_evening = request.dynamic(id="glc_news_evening", {request.create(news_path)})

# Song, then jingle, then song, then jingle.
music = rotate(weights=[1, 1], [songs, jingles])
music = fallback([music, default])

# === Add top-of-the-hour clock jingle (skipped during the news window) ===
music = add([music, switch([({ 0m0s }, clock)])])

# News windows (Pacific): 11:00–11:30 AM and 6:00–6:30 PM.
# Outer fallback track_sensitive=false starts each bulletin on time; inner switch track_sensitive=true
# plays the full bulletin once per window (predicate.once resets daily when the window ends).
radio = fallback(track_sensitive=false, [
  switch(track_sensitive=true, [
    (predicate.once({ 11h0m-11h30m }), news_morning),
    (predicate.once({ 18h0m-18h30m }), news_evening)
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