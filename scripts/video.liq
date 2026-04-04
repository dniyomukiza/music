# HLS via Liquidsoap harbor HTTP (no shared disk with Flask). Nginx proxies https://glc.cool/hls/ → this server.
# Enable: docker compose --profile video up -d
#
# Internal URL (compose network): http://liquidsoap_video:8920/hls/live.m3u8
#
# Setup: media in ./video/ ; paths in ./video/videolist.m3u (container: /liqfolder/video/...)
# Docs: https://www.liquidsoap.info/doc-2.2.5/hls_output.html (output.harbor.hls)

log.stdout := true
settings.harbor.bind_addrs := ["0.0.0.0"]

v = playlist(reload_mode="watch", "/liqfolder/video/videolist.m3u")
v = mksafe(v)

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
