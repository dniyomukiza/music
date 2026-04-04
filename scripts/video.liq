# HLS via Liquidsoap harbor HTTP (no shared disk with Flask). Nginx proxies https://glc.cool/hls/ → this server.
# Enable: docker compose --profile video up -d
#
# Internal URL (compose network): http://liquidsoap_video:8920/hls/live.m3u8
#
# Setup: media in ./video/
#   - videolist.m3u = main programs (order preserved)
#   - tv_jingles.m3u = bumpers; random pick after each program track
# Docs: https://www.liquidsoap.info/doc-2.2.5/hls_output.html (output.harbor.hls)
# Transitions: https://www.liquidsoap.info/doc-2.2.5/video.html
# Use append (not rotate): rotate depends on clean track marks between children;
# with file/FFmpeg video, rotation often stays on the first playlist (jingles never air).

log.stdout := true
settings.harbor.bind_addrs := ["0.0.0.0"]

programs = playlist(reload_mode="watch", "/liqfolder/video/videolist.m3u")
jingles = playlist(mode="random", reload_mode="watch", "/liqfolder/video/tv_jingles.m3u")
# After every program file, play one track from jingles (… → bumper → …).
v = append(programs, fun (_) -> jingles)
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
