const startBtn = document.getElementById('start-btn');
const recordBtn = document.getElementById('record-btn');
const chatLog = document.getElementById('chat-log');
const statusDiv = document.getElementById('status');
let mediaRecorder;
let audioChunks = [];
let initialText = '';
let initialAudioContent = null;
let conversationStarted = false;

// 再生用のAudioContext
const audioContext = new (window.AudioContext || window.webkitAudioContext)();

function playAudio(hexString) {
    const bytes = new Uint8Array(hexString.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
    audioContext.decodeAudioData(bytes.buffer, (buffer) => {
        const source = audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContext.destination);
        source.start(0);
    });
}

// 会話開始ボタン
startBtn.addEventListener('click', async () => {
    statusDiv.textContent = 'AIが会話テーマを提示中...';
    recordBtn.disabled = true;
    chatLog.innerHTML = '';
    conversationStarted = true;
    // サーバーから初回メッセージと音声取得
    const response = await fetch('/start', { method: 'POST' });
    const data = await response.json();
    initialText = data.text;
    initialAudioContent = data.audio_content;
    playAudio(initialAudioContent);
    statusDiv.textContent = 'マイクボタンを押して話してください。';
    recordBtn.disabled = false;
});


// 画面にメッセージを追加する関数
function addMessage(text, className, correction = null) {
    const p = document.createElement('p');
    p.className = className;
    p.textContent = text;
    chatLog.appendChild(p);

    // 添削内容があれば個別に表示
    if (correction && (correction.original || correction.corrected || correction.explanation)) {
        const div = document.createElement('div');
        div.className = 'correction';
        div.innerHTML = `
            <strong>添削内容:</strong><br>
            <b>原文:</b> ${correction.original || '-'}<br>
            <b>修正文:</b> ${correction.corrected || '-'}<br>
            <b>説明:</b> ${correction.explanation || '-'}
        `;
        chatLog.appendChild(div);
    }
    chatLog.scrollTop = chatLog.scrollHeight;
}

// 録音ボタンの制御
recordBtn.addEventListener('mousedown', async () => {
    if (!conversationStarted) return;
    if (mediaRecorder && mediaRecorder.state === 'recording') return;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });

    audioChunks = [];
    mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm;codecs=opus' });
        audioChunks = [];

        const formData = new FormData();
        formData.append('audio', audioBlob);

        try {
            const response = await fetch('/chat', { method: 'POST', body: formData });
            const data = await response.json();

            chatLog.innerHTML = '';
            addMessage(`AI: ${initialText}`, 'ai-text');
            addMessage(`You: ${data.user_text}`, 'user-text', data.correction);
            addMessage(`AI: ${data.ai_text}`, 'ai-text');
            playAudio(data.audio_content);

        } catch (error) {
            console.error('Error:', error);
            addMessage('エラーが発生しました。', 'error-text');
        } finally {
            statusDiv.textContent = 'マイクボタンを押して話してください。';
        }
    };

    mediaRecorder.start();
    recordBtn.textContent = '話しています... (離すと停止)';
    statusDiv.textContent = '録音中...';
});

recordBtn.addEventListener('mouseup', () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        recordBtn.textContent = 'マイクをオンにして話す';
        statusDiv.textContent = 'AIが応答中...';
    }
});

const jpInput = document.getElementById('jp-input');
const translateBtn = document.getElementById('translate-btn');
const enSuggestion = document.getElementById('en-suggestion');

translateBtn.addEventListener('click', async () => {
    const jpText = jpInput.value.trim();
    if (!jpText) {
        enSuggestion.textContent = '日本語を入力してください。';
        return;
    }
    enSuggestion.textContent = '翻訳中...';
    try {
        const response = await fetch('/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jp_text: jpText })
        });
        const data = await response.json();
        if (data.en_text) {
            enSuggestion.textContent = `英語例: ${data.en_text}`;
        } else {
            enSuggestion.textContent = '翻訳できませんでした。';
        }
    } catch (e) {
        enSuggestion.textContent = 'エラーが発生しました。';
    }
});


// 初期化処理：会話を開始
async function startConversation() {
    statusDiv.textContent = '準備中...';
    const response = await fetch('/start', { method: 'POST' });
    const data = await response.json();
    addMessage(`AI: ${data.text}`, 'ai-text');
    playAudio(data.audio_content);
    statusDiv.textContent = 'マイクボタンを押して話してください。';
}

// ページ読み込み時に会話を開始
