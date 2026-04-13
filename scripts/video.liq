# HLS via Liquidsoap harbor HTTP. Nginx proxies https://glc.cool/hls/ → this server.
# Enable: docker compose --profile video up -d
#
# Internal URL (compose network): http://liquidsoap_video:8920/hls/live.m3u8
#
# Playlists list LOCAL FILES ONLY (paths under /liqfolder/…). Liquidsoap does not read YouTube URLs;
# admin TV download stores MP4s on disk, then sync writes those paths into videolist.m3u.
#
# Setup: media in ./video/
#   - videolist.m3u = merged (admin TV sync); lines point at glconnect/static/ytautovid/*.mp4
#   - tv_jingles.m3u = bumper file paths (default: video/tvjingle*.mp4 next to these .m3u files)
# Docs: https://www.liquidsoap.info/doc-2.2.5/hls_output.html (output.harbor.hls)
# Transitions: https://www.liquidsoap.info/doc-2.2.5/video.html
#
# Jingle cadence matches scripts/main.liq (radio): random(weights=[1,2], [jingles, main]) so
# bumpers are interleaved (~1 jingle every 2 program tracks), not only when programs are empty.
# main.liq is audio-only; this file is video+HLS — same operator pattern, different playlists.
# If players glitch on bumper vs program transitions, re-encode bumpers to match program
# resolution and keyframe spacing, or soften weights (e.g. [1, 3]).

log.stdout := true
settings.harbor.bind_addrs := ["0.0.0.0"]

programs = playlist(reload_mode="watch", "/liqfolder/video/videolist.m3u")
jingles = playlist(mode="random", reload_mode="watch", "/liqfolder/video/tv_jingles.m3u")
# Same idea as main.liq: keep a sane main line if one playlist is empty, then interleave jingles.
main_tv = fallback(track_sensitive=false, [programs, jingles])
v = random(weights=[1, 2], [jingles, main_tv])
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
