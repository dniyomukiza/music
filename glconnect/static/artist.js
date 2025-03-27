// Global array to store the playlist
let playlist = [];

// Function to toggle play/pause for an individual song
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

// Function to add a song to the playlist
function addToPlaylist(songId, songName) {
    if (!playlist.some(song => song.id === songId)) {
        playlist.push({ id: songId, name: songName });
        updatePlaylistUI();
    } else {
        alert('This song is already in your playlist!');
    }
}

// Function to update the playlist UI
function updatePlaylistUI() {
    const playlistElement = document.getElementById('playlist');
    playlistElement.innerHTML = ''; // Clear the existing playlist UI

    // Add songs from the playlist array to the UI
    playlist.forEach(song => {
        const songItem = document.createElement('li');
        songItem.textContent = song.name;

        // Add remove button for each song
        const removeButton = document.createElement('button');
        removeButton.textContent = '❌ Remove';
        removeButton.onclick = () => removeFromPlaylist(song.id);

        songItem.appendChild(removeButton);
        playlistElement.appendChild(songItem);
    });
}

// Function to remove a song from the playlist
function removeFromPlaylist(songId) {
    playlist = playlist.filter(song => song.id !== songId);
    updatePlaylistUI();
}

// Function to toggle play/pause for all songs in the playlist
function togglePlayAll() {
    const allAudioElements = document.querySelectorAll('audio');
    const playAllButton = document.getElementById('play-all-button');
    
    // Check if any audio is currently playing
    const isAnyAudioPlaying = Array.from(allAudioElements).some(audio => !audio.paused);
    
    if (isAnyAudioPlaying) {
        // Pause all songs
        allAudioElements.forEach(audio => audio.pause());
        playAllButton.innerHTML = '▶ Play All';
    } else {
        // Play the first song in the playlist and pause others
        const firstAudioElement = document.getElementById(`audio-${playlist[0].id}`);
        firstAudioElement.play();
        
        // Pause all other songs
        allAudioElements.forEach(audio => {
            if (audio !== firstAudioElement) {
                audio.pause();
            }
        });
        
        playAllButton.innerHTML = '⏸ Pause All';
    }
}
// Ensure the playlist is displayed when the page loads
window.onload = function() {
    updatePlaylistUI();
};
