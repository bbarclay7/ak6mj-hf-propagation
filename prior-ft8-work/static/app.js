// Common JavaScript utilities for antenna comparison web app

// Helper for API calls
async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {}
    };

    if (body) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
    }

    const response = await fetch(endpoint, options);
    return response.json();
}

// Format seconds as MM:SS
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${String(secs).padStart(2, '0')}`;
}

// Format ISO timestamp to local time
function formatTimestamp(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString();
}
