const API_BASE = '';

let state = {
    videoId: null,
    paragraphs: [],
    currentIndex: 0,
    isRecording: false,
    mediaRecorder: null,
    audioChunks: [],
    audioPlayer: document.getElementById('audioPlayer'),
};

document.addEventListener('DOMContentLoaded', () => {
    restoreSession();
    setupKeyboardShortcuts();
});

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        switch (e.code) {
            case 'Space':
                e.preventDefault();
                playAudio();
                break;
            case 'KeyR':
                e.preventDefault();
                toggleRecording();
                break;
            case 'ArrowLeft':
                e.preventDefault();
                prevParagraph();
                break;
            case 'ArrowRight':
                e.preventDefault();
                nextParagraph();
                break;
            case 'Escape':
                hideFeedback();
                break;
        }
    });
}

function restoreSession() {
    const saved = localStorage.getItem('shadow_session');
    if (saved) {
        try {
            const session = JSON.parse(saved);
            if (session.videoId && session.url) {
                document.getElementById('videoUrl').value = session.url;
                loadVideo(session.videoId);
            }
        } catch (e) {
            localStorage.removeItem('shadow_session');
        }
    }
}

function saveSession() {
    const session = {
        videoId: state.videoId,
        url: document.getElementById('videoUrl').value,
        currentIndex: state.currentIndex,
    };
    localStorage.setItem('shadow_session', JSON.stringify(session));
}

async function loadVideo(existingId = null) {
    const urlInput = document.getElementById('videoUrl');
    const loadBtn = document.getElementById('loadBtn');
    const statusEl = document.getElementById('loadStatus');

    if (existingId) {
        pollStatus(existingId);
        return;
    }

    const url = urlInput.value.trim();
    if (!url) return;

    loadBtn.disabled = true;
    loadBtn.textContent = 'Loading...';
    statusEl.className = 'status';
    statusEl.classList.remove('hidden');
    statusEl.innerHTML = '<span class="spinner"></span>Fetching video info...';

    try {
        const res = await fetch(`${API_BASE}/api/load`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to load video');
        }

        const data = await res.json();
        if (data.status === 'ready') {
            showPracticeSection(data.video_id);
        } else {
            pollStatus(data.video_id);
        }
    } catch (err) {
        statusEl.className = 'status error';
        statusEl.textContent = `Error: ${err.message}`;
        loadBtn.disabled = false;
        loadBtn.textContent = 'Load';
    }
}

async function pollStatus(videoId) {
    const statusEl = document.getElementById('loadStatus');
    const loadBtn = document.getElementById('loadBtn');

    const poll = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/videos/${videoId}/status`);
            if (!res.ok) throw new Error('Status check failed');

            const data = await res.json();

            if (data.status === 'processing') {
                statusEl.className = 'status';
                statusEl.innerHTML = `<span class="spinner"></span>${data.progress || 'Processing...'}`;
                setTimeout(poll, 2000);
            } else if (data.status === 'ready') {
                showPracticeSection(videoId);
            } else if (data.status === 'error') {
                statusEl.className = 'status error';
                statusEl.textContent = `Error: ${data.error}`;
                loadBtn.disabled = false;
                loadBtn.textContent = 'Load';
            }
        } catch (err) {
            statusEl.className = 'status error';
            statusEl.textContent = `Error: ${err.message}`;
            loadBtn.disabled = false;
            loadBtn.textContent = 'Load';
        }
    };

    poll();
}

async function showPracticeSection(videoId) {
    const statusEl = document.getElementById('loadStatus');
    const loadBtn = document.getElementById('loadBtn');

    try {
        const res = await fetch(`${API_BASE}/api/videos/${videoId}`);
        if (!res.ok) throw new Error('Failed to fetch video data');

        const data = await res.json();

        state.videoId = data.video_id;
        state.paragraphs = data.paragraphs;
        state.currentIndex = 0;

        statusEl.className = 'status success';
        statusEl.textContent = `Loaded: ${data.title} (${data.paragraph_count} paragraphs)`;

        loadBtn.disabled = false;
        loadBtn.textContent = 'Load';

        document.getElementById('practiceSection').classList.remove('hidden');
        renderParagraph();
        saveSession();
    } catch (err) {
        statusEl.className = 'status error';
        statusEl.textContent = `Error: ${err.message}`;
        loadBtn.disabled = false;
        loadBtn.textContent = 'Load';
    }
}

function renderParagraph() {
    const para = state.paragraphs[state.currentIndex];
    if (!para) return;

    document.getElementById('paragraphText').textContent = para.text;
    document.getElementById('paragraphIndicator').textContent =
        `Paragraph ${state.currentIndex + 1} / ${state.paragraphs.length}`;

    document.getElementById('prevBtn').disabled = state.currentIndex === 0;
    document.getElementById('nextBtn').disabled = state.currentIndex === state.paragraphs.length - 1;

    hideFeedback();
    updateAudioSource();
    saveSession();
}

function updateAudioSource() {
    const audioUrl = `${API_BASE}/api/audio/${state.videoId}/${state.currentIndex}`;
    state.audioPlayer.src = audioUrl;
}

function playAudio() {
    const btn = document.getElementById('listenBtn');
    const audio = state.audioPlayer;

    if (audio.paused) {
        audio.play().catch(() => {});
        btn.classList.add('active');
    } else {
        audio.pause();
        btn.classList.remove('active');
    }

    audio.onended = () => btn.classList.remove('active');
}

async function toggleRecording() {
    if (state.isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        state.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        state.audioChunks = [];

        state.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) state.audioChunks.push(e.data);
        };

        state.mediaRecorder.onstop = async () => {
            stream.getTracks().forEach(t => t.stop());
            await submitRecording();
        };

        state.mediaRecorder.start();
        state.isRecording = true;

        const btn = document.getElementById('recordBtn');
        btn.classList.add('recording');
        btn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <rect x="5" y="5" width="8" height="8" rx="2" fill="currentColor"/>
            </svg>
            Stop
        `;
    } catch (err) {
        console.error('Microphone access denied:', err);
        alert('Microphone access is required for recording. Please allow microphone access and try again.');
    }
}

function stopRecording() {
    if (state.mediaRecorder && state.mediaRecorder.state !== 'inactive') {
        state.mediaRecorder.stop();
    }
    state.isRecording = false;

    const btn = document.getElementById('recordBtn');
    btn.classList.remove('recording');
    btn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="5" fill="currentColor"/>
        </svg>
        Record
    `;
}

async function submitRecording() {
    const recordBtn = document.getElementById('recordBtn');
    recordBtn.disabled = true;

    const blob = new Blob(state.audioChunks, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('audio', blob, 'recording.webm');

    try {
        const res = await fetch(
            `${API_BASE}/api/videos/${state.videoId}/paragraphs/${state.currentIndex}/compare`,
            { method: 'POST', body: formData }
        );

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Comparison failed');
        }

        const data = await res.json();
        renderFeedback(data);
    } catch (err) {
        console.error('Comparison error:', err);
        alert(`Error: ${err.message}`);
    } finally {
        recordBtn.disabled = false;
    }
}

function renderFeedback(data) {
    const section = document.getElementById('feedbackSection');
    const diffDisplay = document.getElementById('diffDisplay');
    const accuracyBadge = document.getElementById('accuracyBadge');
    const missingSection = document.getElementById('missingSection');
    const missingText = document.getElementById('missingText');

    section.classList.remove('hidden');

    // Accuracy badge
    const accuracy = data.accuracy || 0;
    accuracyBadge.textContent = `${Math.round(accuracy)}%`;
    accuracyBadge.className = 'accuracy-badge ' +
        (accuracy >= 80 ? 'accuracy-high' : accuracy >= 50 ? 'accuracy-mid' : 'accuracy-low');

    // Diff display
    if (data.diffs && data.diffs.length > 0) {
        diffDisplay.innerHTML = data.diffs.map(d => {
            const word = d.ref || d.user;
            if (!word) return '';
            const cls = `diff-${d.status}`;
            return `<span class="diff-word ${cls}">${escapeHtml(word)}</span>`;
        }).join(' ');
    } else {
        diffDisplay.innerHTML = '<p class="text-muted">No speech detected</p>';
    }

    // Missing section
    if (data.missing && data.missing.length > 0) {
        missingSection.classList.remove('hidden');
        missingText.textContent = data.missing.join(' ');
    } else {
        missingSection.classList.add('hidden');
    }

    section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideFeedback() {
    document.getElementById('feedbackSection').classList.add('hidden');
}

function prevParagraph() {
    if (state.currentIndex > 0) {
        state.currentIndex--;
        renderParagraph();
    }
}

function nextParagraph() {
    if (state.currentIndex < state.paragraphs.length - 1) {
        state.currentIndex++;
        renderParagraph();
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
