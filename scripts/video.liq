# HLS via Liquidsoap harbor HTTP (no shared disk with Flask). Nginx proxies https://glc.cool/hls/ → this server.
# Enable: docker compose --profile video up -d
#
# Internal URL (compose network): http://liquidsoap_video:8920/hls/live.m3u8
#
# Setup: media in ./video/
#   - videolist.m3u = merged from videolist_extra.m3u + DB downloaded_videos (admin TV sync)
#   - tv_jingles.m3u = bumpers (random). Used after each program and as fallback when no programs
# Docs: https://www.liquidsoap.info/doc-2.2.5/hls_output.html (output.harbor.hls)
# Transitions: https://www.liquidsoap.info/doc-2.2.5/video.html
# append: after each resolved program track, play one jingle. fallback keeps bumpers on air
# when videolist has no valid files (deleted shows, wrong paths).

log.stdout := true
settings.harbor.bind_addrs := ["0.0.0.0"]

programs = playlist(reload_mode="watch", "/liqfolder/video/videolist.m3u")
jingles = playlist(mode="random", reload_mode="watch", "/liqfolder/video/tv_jingles.m3u")
with_jingles = append(programs, fun (_) -> jingles)
v = fallback(track_sensitive=false, [with_jingles, jingles])
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
