
log.stdout := true 

# Define the playlists and files
default = single("/liqfolder/jinglemix.ogg")  # Default fallback track
day = playlist("/liqfolder/global.m3u")        # Day playlist
night = playlist("/liqfolder/afro.m3u")      # Night playlist
jingles = playlist("/liqfolder/jingles.m3u")  # Jingles playlist
clock = single("/liqfolder/jinglemix.ogg")         # Clock jingle for top-of-hour

# Create a fallback system for playlists based on time
radio = switch([({ 6h-22h }, day),           # Play 'day' playlist from 6 AM to 10 PM
                ({ 22h-6h }, night)])      # Play 'night' playlist from 10 PM to 6 AM
radio = fallback([radio, default])         # Fallback to default file if something goes wrong

# Add jingles randomly, 1 jingle for every 2 songs
radio = random(weights=[1, 2], [jingles, radio])

# Add the clock jingle at the beginning of each hour
radio = add([radio, switch([({ 0m0s }, clock)])])  # Clock jingle every hour

# Add the ability to relay live shows (if available)
# Pull the stream from the given URL
#live_show = input.harbor("http://localhost:8000/station") 
radio = mksafe(radio)
full = fallback(track_sensitive=false, [
    #live_show,Relay live show if available
    radio       # Use radio if no live show is available
])

# Output the full stream in OGG format
output.icecast(%vorbis,
    host="icecast2", port=8000, password="123", 
    mount="station", full)  # OGG output stream


# **Gospel Stream Setup (Fixed)**
gospel = playlist("/liqfolder/gospel.m3u") 
gospel_radio = mksafe(gospel)
gospel_stream = fallback(track_sensitive=false, [
    gospel_radio
]) 

# **Output Gospel Stream**
output.icecast(%vorbis,
    host="icecast2", port=8000, password="123", 
    mount="gospel", gospel_stream)
