document.addEventListener('DOMContentLoaded', () => {
    const videoUrlInput = document.getElementById('videoUrlInput');
    const getInsightsButton = document.getElementById('getInsightsButton');
    const videoContainer = document.getElementById('videoContainer');
    const insightsContentDiv = document.getElementById('insightsContent');
    const insightsText = document.getElementById('insightsText');
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error');

    getInsightsButton.addEventListener('click', async () => {
        const videoUrl = videoUrlInput.value.trim();

        if (!videoUrl) {
            insightsContentDiv.innerHTML = '<p id="insightsText">Please enter a YouTube video URL.</p>';
            videoContainer.innerHTML = '';
            errorDiv.style.display = 'none';
            return;
        }

        const youtubeRegex = /(?:https?:\/\/)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=|embed\/|v\/|)([\w-]{11})(?:\S+)?/i;
        const match = videoUrl.match(youtubeRegex);

        if (!match || !match[1]) {
            insightsContentDiv.innerHTML = '<p id="insightsText">Invalid YouTube video URL. Please enter a valid URL.</p>';
            videoContainer.innerHTML = '';
            errorDiv.style.display = 'block';
            errorDiv.textContent = 'Error: Invalid YouTube video URL. Please ensure it is a valid YouTube link.';
            return;
        }

        const videoId = match[1];

        insightsContentDiv.innerHTML = '';
        videoContainer.innerHTML = '';
        errorDiv.style.display = 'none';
        loadingDiv.style.display = 'block';

        const embedHtml = `<iframe src="https://www.youtube-nocookie.com/embed/${videoId}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`;
        videoContainer.innerHTML = embedHtml;

        try {
            const response = await fetch('https://yt-transcript-summariser.onrender.com/get-insights', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ video_url: videoUrl }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            insightsContentDiv.innerHTML = marked.parse(data.insights);
            insightsContentDiv.classList.add('fade-in');
            setTimeout(() => insightsContentDiv.classList.remove('fade-in'), 1000);
            errorDiv.style.display = 'none';
        } catch (error) {
            console.error('Error fetching insights:', error);
            insightsContentDiv.innerHTML = '<p>Failed to load insights. Please ensure your API is running and accessible.</p>';
            errorDiv.style.display = 'block';
            errorDiv.textContent = `Error: ${error.message}. Please check your browser console for more details and ensure the API is running with CORS enabled.`;
            videoContainer.innerHTML = '';
        } finally {
            loadingDiv.style.display = 'none';
        }
    });
});
