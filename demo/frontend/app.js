const video = document.getElementById("camera");
const canvas = document.getElementById("capture-canvas");
const canvasContext = canvas.getContext("2d");

const microphoneButton = document.getElementById(
    "microphone-button"
);

const cameraButton = document.getElementById(
    "camera-button"
);

const voiceSelect = document.getElementById(
    "voice-select"
);

const microphoneIcon = document.getElementById(
    "microphone-icon"
);

const microphoneLabel = document.getElementById(
    "microphone-label"
);

const cameraOffMessage = document.getElementById(
    "camera-off-message"
);

let currentStream = null;

// Recording state
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recordingPointerId = null;

// Capture state
let capturedImageBlob = null;
let imageCapturePromise = null;
let imageCaptureTimer = null;

// Request state
let inferenceInProgress = false;

// Text-to-speech state
let availableVoices = [];

const IMAGE_CAPTURE_DELAY_MS = 500;

async function startMedia() {
    try {
        currentStream =
            await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: {
                        ideal: "environment",
                    },
                },
                audio: true,
            });

        const videoTracks =
            currentStream.getVideoTracks();

        videoTracks.forEach((track) => {
            track.enabled = true;
        });

        // The microphone is enabled only while the
        // microphone button is being held.
        const audioTracks =
            currentStream.getAudioTracks();

        audioTracks.forEach((track) => {
            track.enabled = false;
        });

        video.srcObject = currentStream;
        await video.play();

        cameraOffMessage.classList.add("hidden");

        // The camera is always on, so the camera
        // toggle is not needed.
        if (cameraButton) {
            cameraButton.hidden = true;
        }

        updateMicrophoneButton(false);
    } catch (error) {
        console.error(
            "Could not access camera or microphone:",
            error
        );

        cameraOffMessage.textContent =
            "Could not access the camera or microphone.";

        cameraOffMessage.classList.remove("hidden");
    }
}

function beginPressToTalk(event) {
    if (
        !currentStream ||
        isRecording ||
        inferenceInProgress
    ) {
        return;
    }

    event.preventDefault();

    recordingPointerId = event.pointerId;

    microphoneButton.setPointerCapture(
        recordingPointerId
    );

    startAudioRecording();
}

function endPressToTalk(event) {
    if (!isRecording) {
        return;
    }

    if (
        recordingPointerId !== null &&
        event.pointerId !== recordingPointerId
    ) {
        return;
    }

    event.preventDefault();

    if (
        recordingPointerId !== null &&
        microphoneButton.hasPointerCapture(
            recordingPointerId
        )
    ) {
        microphoneButton.releasePointerCapture(
            recordingPointerId
        );
    }

    recordingPointerId = null;

    stopAudioRecording();
}

function startAudioRecording() {
    const audioTracks =
        currentStream.getAudioTracks();

    if (audioTracks.length === 0) {
        console.error(
            "No microphone track is available."
        );

        return;
    }

    audioTracks.forEach((track) => {
        track.enabled = true;
    });

    const audioOnlyStream =
        new MediaStream(audioTracks);

    try {
        mediaRecorder =
            new MediaRecorder(audioOnlyStream);
    } catch (error) {
        console.error(
            "Could not create MediaRecorder:",
            error
        );

        audioTracks.forEach((track) => {
            track.enabled = false;
        });

        return;
    }

    audioChunks = [];
    capturedImageBlob = null;
    imageCapturePromise = null;
    isRecording = true;

    updateMicrophoneButton(true);

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
        handleRecordingStopped,
        {
            once: true,
        }
    );

    mediaRecorder.start();

    imageCaptureTimer = setTimeout(() => {
        if (isRecording) {
            imageCapturePromise = captureImage();
        }
    }, IMAGE_CAPTURE_DELAY_MS);

    console.log("Recording started");
}

function stopAudioRecording() {
    if (!isRecording) {
        return;
    }

    isRecording = false;

    if (imageCaptureTimer !== null) {
        clearTimeout(imageCaptureTimer);
        imageCaptureTimer = null;
    }

    /*
     * For a short button press, the delayed capture
     * may not have happened yet. Capture an image now.
     */
    if (!imageCapturePromise) {
        imageCapturePromise = captureImage();
    }

    if (
        mediaRecorder &&
        mediaRecorder.state === "recording"
    ) {
        mediaRecorder.stop();
    }

    updateMicrophoneButton(false);

    console.log("Recording stopped");
}

async function handleRecordingStopped() {
    const mimeType =
        mediaRecorder?.mimeType ||
        "audio/webm";

    const recordedAudioBlob =
        new Blob(audioChunks, {
            type: mimeType,
        });

    audioChunks = [];

    const audioTracks =
        currentStream?.getAudioTracks() ?? [];

    audioTracks.forEach((track) => {
        track.enabled = false;
    });

    const imageBlob =
        imageCapturePromise
            ? await imageCapturePromise
            : capturedImageBlob;

    imageCapturePromise = null;
    capturedImageBlob = null;
    mediaRecorder = null;

    if (recordedAudioBlob.size === 0) {
        console.error(
            "The recorded audio was empty."
        );

        return;
    }

    console.log(
        "Recorded audio:",
        recordedAudioBlob
    );

    console.log(
        "Captured image:",
        imageBlob
    );

    await handleCompletedTurn(
        recordedAudioBlob,
        imageBlob
    );
}

function captureImage() {
    if (
        video.videoWidth === 0 ||
        video.videoHeight === 0 ||
        video.readyState <
            HTMLMediaElement.HAVE_CURRENT_DATA
    ) {
        console.error(
            "The camera does not have a frame ready."
        );

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

async function handleCompletedTurn(
    audioBlob,
    imageBlob
) {
    if (inferenceInProgress) {
        return;
    }

    inferenceInProgress = true;
    updateMicrophoneButton(false);

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
        const response = await fetch(
            "/inference",
            {
                method: "POST",
                body: formData,
            }
        );

        if (!response.ok) {
            const errorText =
                await response.text();

            throw new Error(
                `Inference failed: ` +
                `${response.status} ${errorText}`
            );
        }

        const result = await response.json();

        console.log(
            "Tutor response:",
            result.response
        );

        speakResponse(result.response);
    } catch (error) {
        console.error(
            "Could not complete tutor turn:",
            error
        );
    } finally {
        inferenceInProgress = false;
        updateMicrophoneButton(false);
    }
}

function updateMicrophoneButton(recording) {
    microphoneButton.classList.toggle(
        "active",
        recording
    );

    microphoneButton.classList.toggle(
        "disabled",
        inferenceInProgress
    );

    microphoneButton.disabled =
        inferenceInProgress;

    microphoneButton.setAttribute(
        "aria-pressed",
        String(recording)
    );

    microphoneButton.setAttribute(
        "aria-label",
        recording
            ? "Release to send"
            : "Hold to speak"
    );

    microphoneIcon.textContent =
        recording ? "🔴" : "🎤";

    microphoneLabel.textContent =
        inferenceInProgress
            ? "Thinking..."
            : recording
                ? "Release to send"
                : "Hold to speak";
}

function loadVoices() {
    availableVoices =
        window.speechSynthesis.getVoices();

    voiceSelect.innerHTML = "";

    const englishVoices =
        availableVoices.filter(
            (voice) =>
                voice.lang
                    .toLowerCase()
                    .startsWith("en")
        );

    const voicesToShow =
        englishVoices.length > 0
            ? englishVoices
            : availableVoices;

    if (voicesToShow.length === 0) {
        const option =
            document.createElement("option");

        option.value = "";
        option.textContent =
            "Default voice";

        voiceSelect.appendChild(option);
        return;
    }

    for (const voice of voicesToShow) {
        const option =
            document.createElement("option");

        option.value = voice.voiceURI;
        option.textContent =
            `${voice.name} (${voice.lang})`;

        if (voice.default) {
            option.textContent +=
                " — Default";
        }

        voiceSelect.appendChild(option);
    }

    const preferredVoice =
        voicesToShow.find(
            (voice) =>
                voice.lang === "en-US" &&
                /natural|neural|enhanced/i.test(
                    voice.name
                )
        ) ??
        voicesToShow.find(
            (voice) =>
                voice.lang === "en-US"
        ) ??
        voicesToShow.find(
            (voice) => voice.default
        ) ??
        voicesToShow[0];

    voiceSelect.value =
        preferredVoice.voiceURI;
}

function speakResponse(text) {
    if (
        !text ||
        !("speechSynthesis" in window)
    ) {
        return;
    }

    const speech =
        new SpeechSynthesisUtterance(text);

    const selectedVoice =
        availableVoices.find(
            (voice) =>
                voice.voiceURI ===
                voiceSelect.value
        );

    if (selectedVoice) {
        speech.voice = selectedVoice;
        speech.lang = selectedVoice.lang;
    }

    speech.rate = 1;
    speech.pitch = 1;
    speech.volume = 1;

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(speech);
}

microphoneButton.addEventListener(
    "pointerdown",
    beginPressToTalk
);

microphoneButton.addEventListener(
    "pointerup",
    endPressToTalk
);

microphoneButton.addEventListener(
    "pointercancel",
    endPressToTalk
);

microphoneButton.addEventListener(
    "lostpointercapture",
    (event) => {
        if (isRecording) {
            endPressToTalk(event);
        }
    }
);

microphoneButton.addEventListener(
    "contextmenu",
    (event) => {
        event.preventDefault();
    }
);

loadVoices();

window.speechSynthesis.addEventListener(
    "voiceschanged",
    loadVoices
);

startMedia();