# HLS via Liquidsoap harbor HTTP. Nginx proxies https://glc.cool/hls/ → this server.
# Enable: docker compose --profile video up -d
#
# Internal URL (compose network): http://liquidsoap_video:8920/hls/live.m3u8
#
# IMPORTANT: Use video/videolist_hls.m3u (single playlist). It is regenerated when Admin TV
# sync runs — interleaved 1 bumper : 2 program tracks from tv_jingles.m3u + videolist.m3u.
# rotate([jingles, programs]) often never selected the jingle branch for video (no tv_jingles
# lines in logs); one playlist makes every file a normal track with clear "Prepared" logs.
#
# Setup: media in ./video/
#   - videolist.m3u = programs only (admin TV sync)
#   - tv_jingles.m3u = bumper paths under /liqfolder/video/...
#   - videolist_hls.m3u = merged order (auto; do not edit by hand)
# Docs: https://www.liquidsoap.info/doc-2.2.5/hls_output.html (output.harbor.hls)

log.stdout := true
settings.harbor.bind_addrs := ["0.0.0.0"]

# playlist() defaults to mode="randomize", which shuffles on reload — bumpers then
# rarely appear early (or seem "missing" in short sessions). Use normal order for
# the pre-interleaved videolist_hls.m3u (see glconnect/pipeline._write_videolist_hls_m3u).
v = playlist(
  id="videolist_hls_m3u",
  reload_mode="watch",
  mode="normal",
  "/liqfolder/video/videolist_hls.m3u"
)
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
