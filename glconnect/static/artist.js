let playlist = [];
let isPlayingAll = false;
let currentAudio = null;
let currentPlaylistIndex = 0;
let songAudioMap = {};

// Toggle play/pause for a single song
function togglePlayPause(songId) {
    const audioElement = document.getElementById(`audio-${songId}`);
    const button = document.querySelector(`button[onclick="togglePlayPause('${songId}')"]`);

    if (audioElement.paused) {
        audioElement.play();
        button.innerHTML = '⏸ Pause';
    } else {
        audioElement.pause();
        button.innerHTML = '▶ Play';
    }
}

function addToPlaylist(songId, songName, userId) {
    // Check if the song is already in the playlist
    if (!playlist.some(song => song.id === songId)) {
        // Add the song to the frontend playlist state
        playlist.push({ id: songId, name: songName });
        
        // Save the new song to the backend
        saveSongToBackend(songId, userId);
    } else {
        alert('This song is already in your playlist!');
    }
}

// Save the newly added song to the backend
function saveSongToBackend(songId, userId) {
    // Instead of sending the whole playlist, just send the newly added song
    fetch('http://glconnect.onrender.com/art/add_to_playlist', {  // Use the add_to_playlist endpoint
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ user_id: userId, song_id: songId })  // Only send the new song
    })
    .then(response => response.json())
    .then(data => alert(data.message))
    .catch(error => {
        console.error("Error saving song to playlist:", error);
        alert("There was an error saving the song to the playlist.");
    });
}


// Toggle play all / pause all
function togglePlayAll() {
    const playAllButton = document.getElementById('play-all-button');
    if (playlist.length === 0) {
        alert("Your playlist is empty! Add songs before playing.");
        return;
    }

    if (isPlayingAll) {
        if (currentAudio) currentAudio.pause();
        playAllButton.innerHTML = '▶ Play All';
        isPlayingAll = false;
    } else {
        if (currentAudio && currentAudio.paused) {
            // Resume where we left off
            currentAudio.play();
        } else {
            currentPlaylistIndex = currentPlaylistIndex || 0;
            playSongSequentially(currentPlaylistIndex);
        }
        playAllButton.innerHTML = '⏸ Pause All';
        isPlayingAll = true;
    }
}

// Sequential playback
function playSongSequentially(index) {
    if (index >= playlist.length) {
        isPlayingAll = false;
        currentPlaylistIndex = 0;
        document.getElementById('play-all-button').innerHTML = '▶ Play All';
        return;
    }

    const song = playlist[index];
    const songUrl = song.song_url;

    if (!songUrl) {
        console.error("Missing song_url for song", song);
        currentPlaylistIndex++;
        playSongSequentially(currentPlaylistIndex);
        return;
    }

    if (!currentAudio || currentAudio.src !== songUrl) {
        currentAudio = new Audio(songUrl);
    }

    currentAudio.play();
    currentAudio.onended = () => {
        currentPlaylistIndex++;
        playSongSequentially(currentPlaylistIndex);
    };

    currentAudio.onerror = () => {
        console.error("Error playing audio:", songUrl);
        currentPlaylistIndex++;
        playSongSequentially(currentPlaylistIndex);
    };
}

// Pause all playback
function pauseAllSongs() {
    if (currentAudio) currentAudio.pause();
    isPlayingAll = false;
    document.getElementById('play-all-button').innerHTML = '▶ Play All';
}

// Save full playlist
function savePlaylist(userId) {
    if (playlist.length === 0) {
        alert("Your playlist is empty! Add songs before saving.");
        return;
    }

    const songIds = playlist.map(song => song.id);

    fetch('http://glconnect.onrender.com/art/save_playlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ user_id: userId, song_ids: songIds })
    })
    .then(response => response.json())
    .then(data => alert(data.message))
    .catch(error => console.error("Error saving playlist:", error));
}

// Delete song from playlist
function deleteSongFromBackend(songId) {
    fetch('http://glconnect.onrender.com/art/delete_song_from_playlist', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ song_id: songId })
    })
    .then(response => response.ok ? response.json() : Promise.reject('Failed'))
    .then(data => alert(data.message))
    .catch(error => {
        console.error("Error:", error);
        alert("There was an error removing the song from the playlist.");
    });
}

// Fetch playlist from backend
function fetchUserPlaylist(userId) {
    fetch(`https://glconnect.onrender.com/art/get_playlist/${userId}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.playlist) {
            const songs = data.playlist;
            playlist = songs.map(song => ({
                id: song.song_id,
                name: song.song_name,
                artist_name: song.artist_name,
                song_url: song.song_url
            }));

            const mydbPlaylistElement = document.getElementById('mydb-playlist');
            mydbPlaylistElement.innerHTML = '';

            songs.forEach(song => {
                const songItem = document.createElement('li');
                songItem.textContent = `${song.song_name} by ${song.artist_name}`;

                const playButton = document.createElement('button');
                playButton.textContent = '▶';
                playButton.onclick = () => playSong(song.song_id, song.artist_name, song.song_name, song.song_url);

                const removeButton = document.createElement('button');
                removeButton.textContent = '❌';
                removeButton.onclick = () => deleteSongFromBackend(song.song_id);

                songItem.appendChild(playButton);
                songItem.appendChild(removeButton);
                mydbPlaylistElement.appendChild(songItem);
            });
        } else {
            console.log("No songs found in the playlist.");
        }
    })
    .catch(error => {
        console.error("Error fetching playlist:", error);
        alert("There was an error fetching your playlist.");
    });
}

// Play individual song
function playSong(songId, artistName, songName, songUrl) {
    const audioFilePath = songUrl || `/static/afro/${encodeURIComponent(artistName)} - ${encodeURIComponent(songName)}.mp3`;
    
    let audioElement = songAudioMap[songId];

    if (!audioElement) {
        audioElement = new Audio(audioFilePath);
        songAudioMap[songId] = audioElement;
    }

    if (!audioElement.paused) {
        audioElement.pause();
        audioElement.currentTime = 0;
    } else {
        audioElement.play();
    }

    const playButton = document.querySelector(`button[onclick="playSong('${songId}', '${artistName}', '${songName}', '${songUrl}')"]`);
    if (playButton) {
        playButton.textContent = audioElement.paused ? '▶ Play' : '⏸ Pause';

        audioElement.onpause = () => {
            playButton.textContent = '▶ Play';
        };
        audioElement.onplay = () => {
            playButton.textContent = '⏸ Pause';
        };
    }
}

// On page load
document.addEventListener("DOMContentLoaded", function () {
    const userId = 5; // Replace with actual user ID
    fetchUserPlaylist(userId);
});
