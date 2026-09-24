# HLS via Liquidsoap harbor HTTP. Nginx proxies https://glc.cool/hls/ → this server.
# Enable: docker compose --profile video up -d
#
# Internal URL (compose network): http://liquidsoap_video:8920/hls/live.m3u8
#
# Two playlists under ./video/ (container: /liqfolder/video/):
#   - tv_jingles.m3u  = bumpers only
#   - videolist.m3u   = programs only (songs)
# rotate(weights=[1,2], …): 1 track from jingles then 2 from programs per round (1:2).
# Prefer this over rotate([jingles, programs, programs]) — the same source listed twice
# can misbehave with video/HLS. For 1:1 use rotate(weights=[1, 1], [jingles, programs]).
#
# If jingles rarely play in practice, fall back to a single pre-merged M3U.
# Docs: https://www.liquidsoap.info/doc-2.2.5/hls_output.html (output.harbor.hls)

log.stdout := true
settings.harbor.bind_addrs := ["0.0.0.0"]

# mode="normal" + reload_mode="watch": stable order and pick up file/M3U changes.
# The news bulletin is the one live program. Open it when the track starts so a
# replaced MP4 is read fresh. If that file is missing or unreadable, play a
# bumper instead of stalling the HLS output.
news_path = "/liqfolder/glconnect/static/ytautovid/The Weeknd - final_news_broadcast.mp4"
news = request.dynamic(id="tv_news", {request.create(news_path)})
jingles = playlist(
  id="tv_jingles_m3u",
  reload_mode="watch",
  mode="normal",
  "/liqfolder/video/tv_jingles.m3u"
)
programs = fallback(track_sensitive=false, [news, jingles])
v = rotate(weights=[1, 2], [jingles, programs])
v = mksafe(v)
v = video.fade.in(transition="fade", duration=3., v)
v = video.fade.out(transition="fade", duration=3., v)

enc_main = %ffmpeg(
  format="mpegts",
  %audio(codec="aac", channels=2, b="128k"),
  %video(
    codec="libx264",
    b="1500k",
    preset="veryfast",
    "x264-params"="scenecut=0:open_gop=0:min-keyint=96:keyint=96"
  )
)

streams = [("main", enc_main)]

output.harbor.hls(
  port=8920,
  path="/hls/",
  playlist="live.m3u8",
  segment_duration=4.0,
  segments=12,
  segments_overhead=6,
  streams,
  v
)
