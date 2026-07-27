const video = document.getElementById("camera");
const canvas = document.getElementById("capture-canvas");
const canvasContext = canvas.getContext("2d");

const microphoneButton = document.getElementById(
    "microphone-button"
);
const cameraButton = document.getElementById(
    "camera-button"
);

const microphoneIcon = document.getElementById(
    "microphone-icon"
);
const cameraIcon = document.getElementById(
    "camera-icon"
);

const microphoneLabel = document.getElementById(
    "microphone-label"
);
const cameraLabel = document.getElementById(
    "camera-label"
);

const cameraOffMessage = document.getElementById(
    "camera-off-message"
);

let currentStream = null;

let microphoneMuted = false;
let cameraEnabled = true;

// Speech-detection state
let audioContext = null;
let analyser = null;
let audioData = null;

let isSpeaking = false;
let silenceStartedAt = null;
let speechImageTimer = null;

// Recording state
let mediaRecorder = null;
let audioChunks = [];

// Results from the most recent speech turn
let recordedAudioBlob = null;
let capturedImageBlob = null;
let imageCapturePromise = null;

const SPEECH_THRESHOLD = 0.02;
const SILENCE_DURATION_MS = 1000;
const IMAGE_CAPTURE_DELAY_MS = 500;

async function startMedia() {
    try {
        currentStream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: {
                    ideal: "environment",
                },
            },
            audio: true,
        });

        video.srcObject = currentStream;
        await video.play();

        setupSpeechDetection();
    } catch (error) {
        console.error(
            "Could not access camera or microphone:",
            error
        );

        cameraOffMessage.textContent =
            "Camera or microphone permission was denied.";

        cameraOffMessage.classList.remove("hidden");
    }
}

function setupSpeechDetection() {
    audioContext = new AudioContext();

    const microphoneSource =
        audioContext.createMediaStreamSource(currentStream);

    analyser = audioContext.createAnalyser();
    analyser.fftSize = 2048;

    microphoneSource.connect(analyser);

    audioData = new Float32Array(analyser.fftSize);

    detectSpeech();
}

function detectSpeech() {
    analyser.getFloatTimeDomainData(audioData);

    let sumSquares = 0;

    for (const sample of audioData) {
        sumSquares += sample * sample;
    }

    const volume = Math.sqrt(
        sumSquares / audioData.length
    );

    const now = performance.now();

    if (
        !microphoneMuted &&
        volume > SPEECH_THRESHOLD
    ) {
        silenceStartedAt = null;

        if (!isSpeaking) {
            handleSpeechStart();
        }
    } else if (isSpeaking) {
        if (silenceStartedAt === null) {
            silenceStartedAt = now;
        }

        const silenceLength =
            now - silenceStartedAt;

        if (silenceLength >= SILENCE_DURATION_MS) {
            handleSpeechEnd();
        }
    }

    requestAnimationFrame(detectSpeech);
}

function handleSpeechStart() {
    isSpeaking = true;
    silenceStartedAt = null;

    recordedAudioBlob = null;
    capturedImageBlob = null;
    imageCapturePromise = null;

    console.log("Speech started");

    startAudioRecording();

    speechImageTimer = setTimeout(() => {
        if (
            isSpeaking &&
            cameraEnabled &&
            video.readyState >=
                HTMLMediaElement.HAVE_CURRENT_DATA
        ) {
            imageCapturePromise = captureImage();
        }
    }, IMAGE_CAPTURE_DELAY_MS);
}

function handleSpeechEnd() {
    isSpeaking = false;
    silenceStartedAt = null;

    console.log("Speech ended");

    if (speechImageTimer !== null) {
        clearTimeout(speechImageTimer);
        speechImageTimer = null;
    }

    stopAudioRecording();
}

function startAudioRecording() {
    const audioTracks = currentStream.getAudioTracks();

    if (audioTracks.length === 0) {
        return;
    }

    const audioOnlyStream = new MediaStream(audioTracks);

    mediaRecorder = new MediaRecorder(audioOnlyStream);
    audioChunks = [];

    mediaRecorder.addEventListener(
        "dataavailable",
        (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        }
    );

    mediaRecorder.addEventListener(
        "stop",
        async () => {
            recordedAudioBlob = new Blob(audioChunks, {
                type: mediaRecorder.mimeType,
            });

            audioChunks = [];

            const imageBlob = imageCapturePromise
                ? await imageCapturePromise
                : capturedImageBlob;

            console.log(
                "Recorded audio:",
                recordedAudioBlob
            );

            console.log(
                "Captured image:",
                imageBlob
            );

            handleCompletedTurn(
                recordedAudioBlob,
                imageBlob
            );
        }
    );

    mediaRecorder.start();
}

function stopAudioRecording() {
    if (
        mediaRecorder &&
        mediaRecorder.state === "recording"
    ) {
        mediaRecorder.stop();
    }
}

function captureImage() {
    if (
        !cameraEnabled ||
        video.videoWidth === 0 ||
        video.videoHeight === 0
    ) {
        return Promise.resolve(null);
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    canvasContext.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
    );

    return new Promise((resolve) => {
        canvas.toBlob(
            (blob) => {
                if (!blob) {
                    console.error(
                        "Could not create image blob."
                    );

                    resolve(null);
                    return;
                }

                capturedImageBlob = blob;

                console.log(
                    "Silent image captured:",
                    capturedImageBlob
                );

                resolve(blob);
            },
            "image/jpeg",
            0.9
        );
    });
}

async function handleCompletedTurn(audioBlob, imageBlob) {
    console.log("Turn completed");

    const formData = new FormData();

    formData.append(
        "audio",
        audioBlob,
        "speech.webm"
    );

    if (imageBlob) {
        formData.append(
            "image",
            imageBlob,
            "frame.jpg"
        );
    }

    try {
        const response = await fetch("/inference", {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            throw new Error(
                `Inference failed: ${response.status}`
            );
        }

        const result = await response.json();

        console.log("Tutor response:", result.response);

        // Display or speak result.response here.
    } catch (error) {
        console.error(
            "Could not complete tutor turn:",
            error
        );
    }
}

function toggleMicrophone() {
    if (!currentStream) {
        return;
    }

    microphoneMuted = !microphoneMuted;

    currentStream.getAudioTracks().forEach((track) => {
        track.enabled = !microphoneMuted;
    });

    if (microphoneMuted && isSpeaking) {
        handleSpeechEnd();
    }

    microphoneButton.classList.toggle(
        "disabled",
        microphoneMuted
    );

    microphoneButton.setAttribute(
        "aria-pressed",
        String(microphoneMuted)
    );

    microphoneButton.setAttribute(
        "aria-label",
        microphoneMuted
            ? "Unmute microphone"
            : "Mute microphone"
    );

    microphoneIcon.textContent =
        microphoneMuted ? "🔇" : "🎤";

    microphoneLabel.textContent =
        microphoneMuted ? "Unmute" : "Mute";
}

function toggleCamera() {
    if (!currentStream) {
        return;
    }

    cameraEnabled = !cameraEnabled;

    currentStream.getVideoTracks().forEach((track) => {
        track.enabled = cameraEnabled;
    });

    cameraButton.classList.toggle(
        "disabled",
        !cameraEnabled
    );

    cameraButton.setAttribute(
        "aria-pressed",
        String(!cameraEnabled)
    );

    cameraButton.setAttribute(
        "aria-label",
        cameraEnabled
            ? "Turn camera off"
            : "Turn camera on"
    );

    cameraIcon.textContent =
        cameraEnabled ? "📹" : "🚫";

    cameraLabel.textContent =
        cameraEnabled
            ? "Video"
            : "Start video";

    cameraOffMessage.classList.toggle(
        "hidden",
        cameraEnabled
    );
}

microphoneButton.addEventListener(
    "click",
    toggleMicrophone
);

cameraButton.addEventListener(
    "click",
    toggleCamera
);

startMedia();