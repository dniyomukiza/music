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
hour_jingle = single("/liqfolder/jinglemix.ogg")
gosp3 = playlist("/liqfolder/eleven.m3u")
satmix = playlist("/liqfolder/eleven.m3u")
eleven = playlist("/liqfolder/eleven.m3u")

# Daily GLC News (raw MP3, request.dynamic only — never playlist/.m3u).
# Container TZ is America/Los_Angeles. Test windows: 11:40–12:00 and 12:01–12:31 PM Pacific.
# The window predicate stays true for the whole half hour so the file has time to
# start. The request function latches after one successful open, so the bulletin
# does not loop, and the latch clears when that window ends. source once() and
# predicate.once() are the wrong tools: once() never re-arms, and predicate.once()
# is only true for the instant the clock ticks.
# Fallible: if final_news_broadcast.mp3 is missing, the slot is skipped and songs stay on.
news_path = "/liqfolder/glconnect/static/audio/final_news_broadcast.mp3"
morning_started = ref(false)
evening_started = ref(false)

def in_morning() =
  t = time.local()
  t.hour == 11 and t.min >= 40
end

def in_evening() =
  t = time.local()
  t.hour == 12 and t.min >= 1 and t.min < 31
end

def morning_request() =
  if morning_started() or not file.exists(news_path) then
    request.create("")
  else
    morning_started := true
    request.create(news_path)
  end
end

def evening_request() =
  if evening_started() or not file.exists(news_path) then
    request.create("")
  else
    evening_started := true
    request.create(news_path)
  end
end

news_morning = request.dynamic(id="glc_news_morning", retry_delay=10., morning_request)
news_evening = request.dynamic(id="glc_news_evening", retry_delay=10., evening_request)

def rearm_news() =
  if not in_morning() then
    morning_started := false
  end
  if not in_evening() then
    evening_started := false
  end
end

thread.run(delay=0., every=5., rearm_news)

# Song, then jingle, then song, then jingle.
music = rotate(weights=[1, 1], [songs, jingles])
music = fallback([music, default])

# Top-of-hour jingle. 12:00 stays a jingle; the next bulletin starts at 12:01.
def play_clock() =
  t = time.local()
  t.min == 0 and t.sec < 2
end

music = add([music, switch([(play_clock, hour_jingle)])])

# News windows (Pacific), test times: 11:40–12:00 and 12:01–12:31 PM.
# track_sensitive=false cuts the current song as soon as the bulletin is ready,
# and the latch above stops a second play before the window closes.
radio = fallback(track_sensitive=false, [
  switch(track_sensitive=false, [
    (in_morning, news_morning),
    (in_evening, news_evening)
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