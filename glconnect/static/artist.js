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
// Ensure playlist is initialized as an array
let playlist = [];

// Function to add a song to the playlist
function addToPlaylist(songId, songName) {
    // Check if the song is already in the playlist
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


function togglePlayAll() {
    const allAudioElements = document.querySelectorAll('audio');
    const playAllButton = document.getElementById('play-all-button');
    
    // If the playlist is empty, do nothing
    if (playlist.length === 0) {
        alert("Your playlist is empty! Add songs before playing.");
        return;
    }
    
    // Check if any audio is currently playing
    const isAnyAudioPlaying = Array.from(allAudioElements).some(audio => !audio.paused);
    
    if (isAnyAudioPlaying) {
        // Pause all songs
        allAudioElements.forEach(audio => audio.pause());
        playAllButton.innerHTML = '▶ Play All';
    } else {
        // Start playing the playlist from the first song
        playSongSequentially(0);
        playAllButton.innerHTML = '⏸ Pause All';
    }
}

// Function to play songs sequentially
function playSongSequentially(index) {
    if (index >= playlist.length) {
        // If we've reached the end of the playlist, stop
        return;
    }

    const song = playlist[index];
    const audioElement = document.getElementById(`audio-${song.id}`);

    if (audioElement) {
        audioElement.play();

        // Set up event listener to play next song when the current one ends
        audioElement.addEventListener('ended', function() {
            playSongSequentially(index + 1); // Play the next song in the playlist
        });
    } else {
        alert(`Audio element for song ${song.name} not found.`);
    }
}

