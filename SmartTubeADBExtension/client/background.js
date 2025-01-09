chrome.action.onClicked.addListener((tab) => {
    // Inject script into the active tab to get the current video URL with timestamp and existing parameters
    chrome.scripting.executeScript({
        target: { tabId: tab.id },
        function: getVideoUrlWithTimestampAndParams
    }, (results) => {
        if (chrome.runtime.lastError || !results || !results[0]) {
            console.error('Failed to get video URL with timestamp and parameters');
            return;
        }

        const videoUrlWithTimestamp = results[0].result;

        // Send POST request to Flask server with updated video URL
        fetch('http://192.168.0.7:8123/play-video', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: videoUrlWithTimestamp }),
        })
        .then(response => response.json())
        .then(data => {
            console.log('Success:', data);

            // Pause YouTube video by injecting a script into the active tab
            chrome.scripting.executeScript({
                target: { tabId: tab.id },
                function: pauseYouTubeVideo
            });
        })
        .catch((error) => {
            console.error('Error:', error);
        });
    });
});

// Function to get YouTube video URL with current timestamp and existing parameters
function getVideoUrlWithTimestampAndParams() {
    const video = document.querySelector('video');
    if (!video) return window.location.href;  // If no video element, return current page URL

    const currentTime = Math.floor(video.currentTime);  // Get current time in seconds
    const url = new URL(window.location.href);

    // Add or update the timestamp parameter (t=seconds)
    url.searchParams.set('t', currentTime);  // No 's' suffix

    return url.toString();  // Return updated URL with timestamp and other existing parameters
}

// Function to pause YouTube video
function pauseYouTubeVideo() {
    const video = document.querySelector('video');
    if (video && !video.paused) {
        video.pause();
    }
}