document.addEventListener('DOMContentLoaded', () => {
    // --- Get references to all elements ---
    const videoUrlInput = document.getElementById('videoUrlInput');
    const getInsightsButton = document.getElementById('getInsightsButton');
    const videoContainer = document.getElementById('videoContainer');
    const insightsContentDiv = document.getElementById('insightsContent');
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error');
    const downloadPdfButton = document.getElementById('download-pdf');

    // --- Variables to store data from the API ---
    let rawMarkdownContent = '';
    let videoTitle = ''; 

    // --- PDF Download Logic ---
    downloadPdfButton.addEventListener('click', async () => {
        if (!rawMarkdownContent) {
            alert("No insights content to download.");
            return;
        }

        const response = await fetch('/download-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                // **FIX:** Send the correct variable names
                title: videoTitle,
                markdown_content: rawMarkdownContent 
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `[summarized]${videoTitle}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } else {
            alert('Failed to download PDF.');
        }
    });

    // --- Get Insights Logic ---
    getInsightsButton.addEventListener('click', async () => {
        // --- Reset UI for new request ---
        const videoUrl = videoUrlInput.value.trim();
        insightsContentDiv.innerHTML = '';
        videoContainer.innerHTML = '';
        errorDiv.style.display = 'none';
        rawMarkdownContent = '';
        videoTitle = ''; 
        downloadPdfButton.disabled = true;

        if (!videoUrl) {
            errorDiv.style.display = 'block';
            errorDiv.textContent = 'Please enter a YouTube video URL.';
            return;
        }

        const youtubeRegex = /(?:https?:\/\/)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=|embed\/|v\/|)([\w-]{11})(?:\S+)?/i;
        const match = videoUrl.match(youtubeRegex);

        if (!match || !match[1]) {
            errorDiv.style.display = 'block';
            errorDiv.textContent = 'Error: Invalid YouTube video URL.';
            return;
        }

        const videoId = match[1];
        loadingDiv.style.display = 'block';
        videoContainer.innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${videoId}" frameborder="0" allowfullscreen></iframe>`;

        try {
            const response = await fetch('http://127.0.0.1:8000/get-insights', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ video_url: videoUrl }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            
            // **FIX:** Store both title and insights in variables
            videoTitle = data.title || 'Untitled Video';
            rawMarkdownContent = data.insights || '';

            // Render the HTML using the stored variables, including the title
            insightsContentDiv.innerHTML = `<h1>${videoTitle}</h1>` + (marked.parse(rawMarkdownContent) || '<p>No insights received.</p>');
            
            downloadPdfButton.disabled = false;

        } catch (error) {
            console.error('Error fetching insights:', error);
            errorDiv.style.display = 'block';
            errorDiv.textContent = `Error: ${error.message}`;
            videoContainer.innerHTML = '';
        } finally {
            loadingDiv.style.display = 'none';
        }
    });
});