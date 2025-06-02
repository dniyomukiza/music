let playlist = [];
let isPlayingAll = false;
let currentAudio = null;
let currentPlaylistIndex = 0;
const songAudioMap = new Map();

// Helper: Encode URL for iOS Safari compatibility
function encodeUrl(url) {
    return encodeURI(url).replace(/#/g, '%23');
}

// Toggle play/pause for a single song
function togglePlayPause(songId) {
    const audio = songAudioMap.get(songId);
    if (!audio) return;

    if (audio.paused) {
        audio.play();
    } else {
        audio.pause();
    }
}

// Add a song to the playlist
function addToPlaylist(songId, songName, userId) {
    if (!playlist.some(song => song.id === songId)) {
        playlist.push({ id: songId, name: songName });
        saveSongToBackend(songId, userId);
    } else {
        alert('This song is already in your playlist!');
    }
}

// Save a new song to the backend
function saveSongToBackend(songId, userId) {
    fetch('https://www.glc.cool/art/add_to_playlist', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ user_id: userId, song_id: songId })
    })
    .then(res => res.json())
    .then(data => alert(data.message))
    .catch(err => {
        console.error("Error saving song:", err);
        alert("Failed to save the song to your playlist.");
    });
}

// Play all songs sequentially
function togglePlayAll() {
    const playAllButton = document.getElementById('play-all-button');
    if (!playlist.length) return alert("Your playlist is empty!");

    if (isPlayingAll) {
        if (currentAudio) currentAudio.pause();
        isPlayingAll = false;
        playAllButton.textContent = '▶ Play All';
    } else {
        currentPlaylistIndex = 0;
        isPlayingAll = true;
        playSongSequentially(currentPlaylistIndex);
        playAllButton.textContent = '⏸ Pause All';
    }
}

// Recursive playback
function playSongSequentially(index) {
    if (index >= playlist.length) {
        isPlayingAll = false;
        document.getElementById('play-all-button').textContent = '▶ Play All';
        return;
    }

    const song = playlist[index];
    const audio = new Audio(encodeUrl(song.song_url));
    currentAudio = audio;
    audio.play();

    audio.onended = () => {
        currentPlaylistIndex++;
        playSongSequentially(currentPlaylistIndex);
    };

    audio.onerror = () => {
        console.error(`Error playing: ${song.song_url}`);
        currentPlaylistIndex++;
        playSongSequentially(currentPlaylistIndex);
    };
}

// Save entire playlist
function savePlaylist(userId) {
    if (!playlist.length) return alert("Your playlist is empty!");

    const songIds = playlist.map(song => song.id);
    fetch('https://www.glc.cool/art/save_playlist', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ user_id: userId, song_ids: songIds })
    })
    .then(res => res.json())
    .then(data => alert(data.message))
    .catch(err => console.error("Error saving playlist:", err));
}

// Delete a song from backend and update UI
function deleteSongFromBackend(songId) {
    fetch('https://www.glc.cool/art/delete_song_from_playlist', {
        method: 'DELETE',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ song_id: songId })
    })
    .then(res => res.ok ? res.json() : Promise.reject('Failed'))
    .then(data => {
        alert(data.message);
        playlist = playlist.filter(song => song.id !== songId);
        fetchUserPlaylist(currentUserId);
    })
    .catch(err => {
        console.error("Delete error:", err);
        alert("Error removing song from playlist.");
    });
}

// Fetch playlist from backend
function fetchUserPlaylist(userId) {
    fetch(`https://www.glc.cool/art/get_playlist/${userId}`, {
        method: 'GET',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }
    })
    .then(res => res.json())
    .then(data => {
        if (!data.playlist) return;

        playlist = data.playlist.map(song => ({
            id: song.song_id,
            name: song.song_name,
            artist_name: song.artist_name,
            song_url: song.song_url
        }));

        const playlistElement = document.getElementById('mydb-playlist');
        playlistElement.innerHTML = '';

        playlist.forEach(song => {
            const li = document.createElement('li');
            li.textContent = `${song.name} by ${song.artist_name}`;

            const playBtn = document.createElement('button');
            playBtn.textContent = '▶';
            playBtn.addEventListener('click', () => playSong(song));

            const removeBtn = document.createElement('button');
            removeBtn.textContent = '❌';
            removeBtn.addEventListener('click', () => deleteSongFromBackend(song.id));

            li.appendChild(playBtn);
            li.appendChild(removeBtn);
            playlistElement.appendChild(li);
        });
    })
    .catch(err => {
        console.error("Error loading playlist:", err);
        alert("Could not load your playlist.");
    });
}

// Play a single song with toggle
function playSong(song) {
    if (!songAudioMap.has(song.id)) {
        const audio = new Audio(encodeUrl(song.song_url));
        songAudioMap.set(song.id, audio);
    }

    const audio = songAudioMap.get(song.id);
    if (!audio) return;

    if (!audio.paused) {
        audio.pause();
        audio.currentTime = 0;
    } else {
        audio.play();
    }

    audio.onplay = () => updatePlayButton(song.id, '⏸ Pause');
    audio.onpause = () => updatePlayButton(song.id, '▶ Play');
}

// Update button text by ID
function updatePlayButton(songId, text) {
    const buttons = document.querySelectorAll('#mydb-playlist li button');
    buttons.forEach(btn => {
        if (btn.onclick && btn.onclick.toString().includes(songId)) {
            btn.textContent = text;
        }
    });
}

// Replace with dynamic user ID logic
let currentUserId = 5;

// On page load
document.addEventListener("DOMContentLoaded", () => {
    fetchUserPlaylist(currentUserId);
});
