# Optional standalone video → HLS (H.264 + AAC) for browser playback (Safari native, Chrome/Firefox via hls.js).
# Not included from main.liq. Enable: docker compose --profile video up -d
#
# Watch: https://glc.cool/static/video_live.html  (manifest: /hls/live.m3u8)
#
# Setup:
#   1. Media in ./video/ ; paths in ./video/videolist.m3u (container: /liqfolder/video/...)
#   2. HLS segments written to ./hls-video/ ; nginx serves /hls/ from that directory
#
# Docs: https://www.liquidsoap.info/doc-2.2.5/hls_output.html

log.stdout := true

v = playlist(reload_mode="watch", "/liqfolder/video/videolist.m3u")
v = mksafe(v)

# Single browser-friendly rendition: MPEG-TS + AAC + H.264 (RFC 8216–friendly via ffmpeg)
enc_main = %ffmpeg(
  format="mpegts",
  %audio(codec="aac", channels=2, ar=44100, b="128k"),
  %video(
    codec="libx264",
    b="1500k",
    preset="veryfast",
    "x264-params"="scenecut=0:open_gop=0:min-keyint=96:keyint=96"
  )
)

streams = [("main", enc_main)]

output.file.hls(
  playlist="live.m3u8",
  segment_duration=4.0,
  segments=12,
  segments_overhead=6,
  "/liqfolder/hls-video",
  streams,
  v
)
