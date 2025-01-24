


# Music playlist (fallible source)
myplaylist = playlist("/liqfolder/gospel.m3u")

# Jingles playlist (fallible source)
jingles = playlist("/liqfolder/jingles.m3u")

# Security fallback (infallible source)
security = single("/liqfolder/dash.ogg")

# Combine music and jingles (fallible sources)
radio = random(weights = [1, 5], [jingles, myplaylist])

# Make the radio source infallible using mksafe
radio = mksafe(radio)

# Ensure the stream is infallible with a fallback
radio = fallback(track_sensitive = false, [radio, security])

# Stream to Icecast
output.icecast(%vorbis,
  host = "icecast2", port = 8000,
  password ="123", mount = "turnup",
  radio)




