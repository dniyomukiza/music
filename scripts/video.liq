# Optional standalone video → Icecast (do NOT include from main.liq).
# Run only via: docker compose --profile video up -d
#
# Setup:
#   1. Add files under ./video/ on the host.
#   2. Edit ./video/videolist.m3u — one absolute-in-container path per line, e.g.:
#        /liqfolder/video/myclip.mp4
#   3. Icecast must accept mount "video" (see icecast.xml).
#
# To turn off: omit --profile video, or: docker compose --profile video stop liquidsoap_video
# To remove this feature entirely: delete this file, the video/ folder contents you added,
#   and the liquidsoap_video service from docker-compose.yml.

log.stdout := true

v = playlist(reload_mode="watch", "/liqfolder/video/videolist.m3u")
v = mksafe(v)

output.icecast(
  %ffmpeg(
    format="ogg",
    %audio(codec="libvorbis"),
    %video(codec="libtheora")
  ),
  host="icecast2",
  port=8000,
  password="123",
  mount="video",
  name="Video (optional)",
  description="Self-contained Liquidsoap video experiment",
  v
)
