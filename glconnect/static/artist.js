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
// Function to add a song to the playlist
function addToPlaylist(songId, songName, userId) {
    // Check if the song is already in the playlist
    if (!playlist.some(song => song.id === songId)) {
        playlist.push({ id: songId, name: songName });

        // After adding to the playlist, save to backend
        saveSongToBackend(songId, userId);
    } else {
        alert('This song is already in your playlist!');
    }
}

// Function to save the song to the backend (called after adding to playlist)
function saveSongToBackend(songId, userId) {
    // Prepare the playlist with the current song added
    const songIds = playlist.map(song => song.id);

    fetch('http://127.0.0.1:5000/art/save_playlist', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',  // Ensure JSON format
            'Accept': 'application/json'
        },
        body: JSON.stringify({ user_id: userId, song_ids: songIds })
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);  // Show response message from the backend
    })
    .catch(error => {
        console.error("Error saving song to playlist:", error);
        alert("There was an error saving the song to the playlist.");
    });
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

function savePlaylist(userId) {
    if (playlist.length === 0) {
        alert("Your playlist is empty! Add songs before saving.");
        return;
    }

    const songIds = playlist.map(song => song.id);

    fetch('http://127.0.0.1:5000/art/save_playlist', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',  // Ensure JSON format
            'Accept': 'application/json'
        },
        body: JSON.stringify({ user_id: userId, song_ids: songIds })
    })
    .then(response => response.json())
    .then(data => alert(data.message))
    .catch(error => console.error("Error saving playlist:", error));
}
fetch('http://127.0.0.1:5000/art/save_playlist', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json', 
        'Accept': 'application/json'
    },
    body: JSON.stringify({ user_id: 1, song_ids: [101, 102] }) 
})
.then(response => response.json())
.then(data => console.log("Response:", data))
.catch(error => console.error("Error:", error));

function deleteSongFromBackend(songId) {
    fetch('http://127.0.0.1:5000/art/delete_song_from_playlist', {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        body: JSON.stringify({ song_id: songId })
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        } else {
            throw new Error('Failed to remove song from playlist');
        }
    })
    .then(data => {
        alert(data.message);
    })
    .catch(error => {
        console.error("Error:", error);
        alert("There was an error removing the song from the playlist.");
    });
}


// Function to fetch a specific user's songs from the playlist table
function fetchUserPlaylist(userId) {
    fetch(`http://127.0.0.1:5000/art/get_playlist/${userId}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.playlist) {
            // Process the list of songs in the playlist
            const songs = data.playlist;
            console.log("User's Playlist:", songs);
            
            // Update the "MyDB" section with the user's playlist songs
            const mydbPlaylistElement = document.getElementById('mydb-playlist');
            mydbPlaylistElement.innerHTML = '';  // Clear any existing songs

            songs.forEach(song => {
                const songItem = document.createElement('li');
                songItem.textContent = `${song.song_name} by ${song.artist_name}`;  // Display song name and artist name

                // Create the "Play" button
                const playButton = document.createElement('button');
                playButton.textContent = '▶';
                playButton.onclick = () => playSong(song.song_id); // Implement playSong function if needed

                // Create the "Remove" button
                const removeButton = document.createElement('button');
                removeButton.textContent = '❌';
                removeButton.onclick = () => deleteSongFromBackend(song.song_id); // Call the function to remove the song
                
                // Append the buttons to the song item
                songItem.appendChild(playButton);
                songItem.appendChild(removeButton);
                
                // Append the song item to the playlist element
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

// Wait for the DOM to be ready before calling the function
document.addEventListener("DOMContentLoaded", function() {
    const userId = 5; // Replace with the actual logged-in user ID
    fetchUserPlaylist(userId);
});
