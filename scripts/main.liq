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

# Daily GLC News (raw MP3, single/once only — never playlist/.m3u).
# TEST slots (Pacific, TZ=America/Los_Angeles): 7:30–8:00 PM and 8:30–9:00 PM.
# Switch back to 11:00 AM / 6:00 PM Pacific when testing is done.
# Separate once() per window so each slot plays the bulletin once, then music resumes.
# Fallible: if final_news_broadcast.mp3 is missing, the slot is skipped and jingles/songs stay on.
news_path = "/liqfolder/glconnect/static/audio/final_news_broadcast.mp3"
news_morning = once(single(news_path))
news_evening = once(single(news_path))

# Song, then jingle, then song, then jingle.
music = rotate(weights=[1, 1], [songs, jingles])
music = fallback([music, default])

# === Add top-of-the-hour clock jingle (skipped during the news window) ===
music = add([music, switch([({ 0m0s }, clock)])])

# TEST news windows (Pacific): 7:30–8:00 PM and 8:30–9:00 PM.
# track_sensitive=false starts each bulletin on time; after it ends, music resumes until the window closes.
radio = fallback(track_sensitive=false, [
  switch(track_sensitive=false, [
    ({ 19h30m-20h0m }, news_morning),
    ({ 20h30m-21h0m }, news_evening)
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