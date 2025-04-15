log.stdout := true

# Gospel Playlist
gospel = playlist("/liqfolder/gosp3.m3u")  # Ensure the path is correct

# Output Gospel Stream in MP3 format
output.icecast(%mp3, 
  host="icecast2", 
  port=8000, 
  password="123", 
  mount="gosp3",   # Ensure the mount name is correct in Icecast
  bitrate=128, 
  gospel)
