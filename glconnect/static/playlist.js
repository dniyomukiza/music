document.addEventListener('DOMContentLoaded', function () {
    const playButtons = document.querySelectorAll('.play-button');

    playButtons.forEach(button => {
        button.addEventListener('click', function () {
            const songName = this.getAttribute('data-song');
            const artistName = this.getAttribute('data-artist');
            
            fetch('/search_song_features', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ song_name: songName, artist_name: artistName })
            })
            .then(response => response.json())
            .then(features => {
                console.log(features); // Display the song features in the console or UI
                alert('Now Playing: ' + songName);
                // Add logic to play the song here
            });
        });
    });
});
