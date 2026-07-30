const video = document.getElementById("camera");
const canvas = document.getElementById("capture-canvas");
const canvasContext = canvas.getContext("2d");

const beginOverlay = document.getElementById(
    "begin-overlay"
);

const beginButton = document.getElementById(
    "begin-button"
);

const cameraAudioButton = document.getElementById(
    "camera-audio-button"
);

const audioOnlyButton = document.getElementById(
    "audio-only-button"
);

const checkpointText = document.getElementById(
    "checkpoint-text"
);

const cameraOffMessage = document.getElementById(
    "camera-off-message"
);

const whiteboardButton = document.getElementById(
    "whiteboard-button"
);

const whiteboardOverlay = document.getElementById(
    "whiteboard-overlay"
);

const whiteboardPanel = document.getElementById(
    "whiteboard-panel"
);

const whiteboardCloseButton = document.getElementById(
    "whiteboard-close-button"
);

const conversationElement = document.getElementById(
    "correct-steps"
);

const IMAGE_CAPTURE_DELAY_MS = 1000;

const AudioContextClass =
    window.AudioContext ||
    window.webkitAudioContext;

const tutorAudioContext =
    AudioContextClass
        ? new AudioContextClass()
        : null;

let activeTutorAudioSource = null;

let currentStream = null;
let mediaRecorder = null;
let audioChunks = [];

let isRecording = false;
let inferenceInProgress = false;
let whiteboardOpen = false;

let activeButton = null;
let activePointerId = null;
let includeImageForTurn = false;

let imageCaptureTimer = null;
let imageCapturePromise = null;
let capturedImageBlob = null;

let conversationHistory = [];


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

        const audioTracks =
            currentStream.getAudioTracks();

        audioTracks.forEach((track) => {
            track.enabled = false;
        });

        video.srcObject = currentStream;

        await video.play();

        cameraOffMessage.classList.add(
            "hidden"
        );

        updateButtons();

        return true;
    } catch (error) {
        console.error(
            "Could not access camera or microphone:",
            error
        );

        cameraOffMessage.textContent =
            "Could not access the camera or microphone.";

        cameraOffMessage.classList.remove(
            "hidden"
        );

        return false;
    }
}


function playGreetingAudio() {
    if (!("speechSynthesis" in window)) {
        console.error(
            "Browser text-to-speech is unavailable."
        );

        return;
    }

    window.speechSynthesis.cancel();

    const speech =
        new SpeechSynthesisUtterance(
            "Hello!"
        );

    speech.lang = "en-US";
    speech.rate = 0.95;
    speech.pitch = 1;
    speech.volume = 1;

    speech.onerror = (event) => {
        console.error(
            "Greeting speech failed:",
            event.error,
            event
        );
    };

    window.speechSynthesis.speak(speech);
}


function enableTutorAudio() {
    if (!tutorAudioContext) {
        console.error(
            "Web Audio is unavailable."
        );

        return;
    }

    tutorAudioContext
        .resume()
        .catch((error) => {
            console.error(
                "Could not enable tutor audio:",
                error
            );
        });
}


async function beginTutor() {
    beginButton.disabled = true;
    beginButton.textContent = "Starting…";

    playGreetingAudio();
    enableTutorAudio();

    const mediaStarted =
        await startMedia();

    if (!mediaStarted) {
        beginButton.disabled = false;
        beginButton.textContent = "Try Again";

        return;
    }

    beginOverlay.remove();
}


function beginHold(event, includeImage) {
    if (
        !currentStream ||
        isRecording ||
        inferenceInProgress
    ) {
        return;
    }

    if (includeImage && whiteboardOpen) {
        return;
    }

    event.preventDefault();

    activeButton = event.currentTarget;
    activePointerId = event.pointerId;
    includeImageForTurn = includeImage;

    activeButton.setPointerCapture(
        activePointerId
    );

    startRecording();
}


function endHold(event) {
    if (!isRecording) {
        return;
    }

    if (
        activePointerId !== null &&
        event.pointerId !== activePointerId
    ) {
        return;
    }

    event.preventDefault();

    if (
        activeButton &&
        activePointerId !== null &&
        activeButton.hasPointerCapture(
            activePointerId
        )
    ) {
        activeButton.releasePointerCapture(
            activePointerId
        );
    }

    activePointerId = null;

    stopRecording();
}


function startRecording() {
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

    setStatus("Listening");
    updateButtons();

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

    if (includeImageForTurn) {
        imageCaptureTimer = setTimeout(
            () => {
                if (isRecording) {
                    imageCapturePromise =
                        captureImage();
                }
            },
            IMAGE_CAPTURE_DELAY_MS
        );
    }
}


function stopRecording() {
    if (!isRecording) {
        return;
    }

    isRecording = false;

    if (imageCaptureTimer !== null) {
        clearTimeout(imageCaptureTimer);
        imageCaptureTimer = null;
    }

    if (
        includeImageForTurn &&
        !imageCapturePromise
    ) {
        imageCapturePromise =
            captureImage();
    }

    if (
        mediaRecorder &&
        mediaRecorder.state === "recording"
    ) {
        mediaRecorder.stop();
    }

    updateButtons();
}


async function handleRecordingStopped() {
    const mimeType =
        mediaRecorder?.mimeType ||
        "audio/webm";

    const recordedAudioBlob =
        new Blob(audioChunks, {
            type: mimeType,
        });

    const audioTracks =
        currentStream?.getAudioTracks() ??
        [];

    audioTracks.forEach((track) => {
        track.enabled = false;
    });

    let imageBlob = null;

    if (includeImageForTurn) {
        imageBlob = imageCapturePromise
            ? await imageCapturePromise
            : capturedImageBlob;
    }

    const includedImage =
        includeImageForTurn;

    audioChunks = [];
    imageCapturePromise = null;
    capturedImageBlob = null;
    mediaRecorder = null;
    activeButton = null;
    activePointerId = null;
    includeImageForTurn = false;

    if (recordedAudioBlob.size === 0) {
        console.error(
            "The recorded audio was empty."
        );

        setStatus("");
        updateButtons();

        return;
    }

    await handleCompletedTurn(
        recordedAudioBlob,
        imageBlob,
        includedImage
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

                resolve(blob);
            },
            "image/jpeg",
            0.9
        );
    });
}


async function handleCompletedTurn(
    audioBlob,
    imageBlob,
    includedImage
) {
    if (inferenceInProgress) {
        return;
    }

    inferenceInProgress = true;

    setStatus("Reasoning");
    updateButtons();

    const formData =
        new FormData();

    formData.append(
        "audio",
        audioBlob,
        "speech.webm"
    );

    if (includedImage && imageBlob) {
        formData.append(
            "image",
            imageBlob,
            "frame.jpg"
        );
    }

    try {
        const response = await fetch(
            "/stream_pipeline",
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

        const data =
            await response.json();

        if (!Array.isArray(data.conversation)) {
            throw new Error(
                "The backend did not return a conversation array."
            );
        }

        conversationHistory =
            data.conversation;

        await renderConversationHistory();

        if (
            typeof data.base64_audio ===
                "string" &&
            data.base64_audio.length > 0
        ) {
            await playTutorAudio(
                data.base64_audio
            );
        }

        setStatus("");
    } catch (error) {
        console.error(
            "Could not complete tutor turn:",
            error
        );

        setStatus("Error");
    } finally {
        inferenceInProgress = false;

        updateButtons();
    }
}


async function renderConversationHistory() {
    if (!conversationElement) {
        return;
    }

    if (window.MathJax?.typesetClear) {
        window.MathJax.typesetClear(
            [conversationElement]
        );
    }

    conversationElement.innerHTML = "";

    if (conversationHistory.length === 0) {
        const emptyMessage =
            document.createElement("p");

        emptyMessage.className =
            "empty-message";

        emptyMessage.textContent =
            "Ask the tutor a question to begin.";

        conversationElement.appendChild(
            emptyMessage
        );

        return;
    }

    for (const turn of conversationHistory) {
        const role =
            turn?.role === "assistant"
                ? "assistant"
                : "user";

        const turnElement =
            document.createElement("div");

        turnElement.className =
            `conversation-turn conversation-${role}`;

        const roleElement =
            document.createElement("div");

        roleElement.className =
            "conversation-role";

        roleElement.textContent =
            role === "assistant"
                ? "Tutor"
                : "You";

        const contentElement =
            document.createElement("div");

        contentElement.className =
            "conversation-content";

        contentElement.textContent =
            String(turn?.content ?? "");

        turnElement.appendChild(
            roleElement
        );

        turnElement.appendChild(
            contentElement
        );

        conversationElement.appendChild(
            turnElement
        );
    }

    if (window.MathJax?.typesetPromise) {
        try {
            await window.MathJax.typesetPromise(
                [conversationElement]
            );
        } catch (error) {
            console.error(
                "Could not render LaTeX:",
                error
            );
        }
    }

    scrollConversationToBottom();
}


function scrollConversationToBottom() {
    requestAnimationFrame(() => {
        conversationElement.scrollTop =
            conversationElement.scrollHeight;
    });
}


async function playTutorAudio(
    base64Audio
) {
    try {
        if (!tutorAudioContext) {
            throw new Error(
                "Web Audio is unavailable."
            );
        }

        const audioBytes =
            base64ToArrayBuffer(
                base64Audio
            );

        if (audioBytes.byteLength === 0) {
            throw new Error(
                "The tutor audio was empty."
            );
        }

        if (
            tutorAudioContext.state !==
            "running"
        ) {
            await tutorAudioContext.resume();
        }

        const decodedAudio =
            await tutorAudioContext.decodeAudioData(
                audioBytes.slice(0)
            );

        if (activeTutorAudioSource) {
            try {
                activeTutorAudioSource.stop();
            } catch {
                // The previous audio already ended.
            }

            activeTutorAudioSource = null;
        }

        const source =
            tutorAudioContext.createBufferSource();

        source.buffer = decodedAudio;

        source.connect(
            tutorAudioContext.destination
        );

        source.onended = () => {
            if (
                activeTutorAudioSource ===
                source
            ) {
                activeTutorAudioSource = null;
            }
        };

        activeTutorAudioSource = source;

        source.start(0);
    } catch (error) {
        console.error(
            "Could not play tutor audio:",
            error
        );

        setStatus("Audio error");
    }
}


function base64ToArrayBuffer(base64Audio) {
    const binaryString =
        window.atob(base64Audio);

    const bytes =
        new Uint8Array(
            binaryString.length
        );

    for (
        let index = 0;
        index < binaryString.length;
        index += 1
    ) {
        bytes[index] =
            binaryString.charCodeAt(index);
    }

    return bytes.buffer;
}


function setStatus(text) {
    if (!checkpointText) {
        return;
    }

    checkpointText.textContent =
        text ? `${text}…` : "";

    checkpointText.classList.toggle(
        "hidden",
        !text
    );
}


async function openWhiteboard() {
    whiteboardOpen = true;

    whiteboardOverlay.classList.remove(
        "hidden"
    );

    whiteboardOverlay.setAttribute(
        "aria-hidden",
        "false"
    );

    await renderConversationHistory();

    updateButtons();
}


function closeWhiteboard() {
    whiteboardOpen = false;

    whiteboardOverlay.classList.add(
        "hidden"
    );

    whiteboardOverlay.setAttribute(
        "aria-hidden",
        "true"
    );

    updateButtons();
}


function updateButtons() {
    const cameraAudioDisabled =
        inferenceInProgress ||
        whiteboardOpen;

    const audioOnlyDisabled =
        inferenceInProgress;

    cameraAudioButton.disabled =
        cameraAudioDisabled;

    audioOnlyButton.disabled =
        audioOnlyDisabled;

    cameraAudioButton.classList.toggle(
        "disabled",
        cameraAudioDisabled
    );

    audioOnlyButton.classList.toggle(
        "disabled",
        audioOnlyDisabled
    );

    cameraAudioButton.classList.toggle(
        "active",
        isRecording &&
            activeButton ===
                cameraAudioButton
    );

    audioOnlyButton.classList.toggle(
        "active",
        isRecording &&
            activeButton ===
                audioOnlyButton
    );

    cameraAudioButton.setAttribute(
        "aria-pressed",
        String(
            isRecording &&
                activeButton ===
                    cameraAudioButton
        )
    );

    audioOnlyButton.setAttribute(
        "aria-pressed",
        String(
            isRecording &&
                activeButton ===
                    audioOnlyButton
        )
    );
}


function bindHoldButton(
    button,
    includeImage
) {
    button.addEventListener(
        "pointerdown",
        (event) => {
            beginHold(
                event,
                includeImage
            );
        }
    );

    button.addEventListener(
        "pointerup",
        endHold
    );

    button.addEventListener(
        "pointercancel",
        endHold
    );

    button.addEventListener(
        "lostpointercapture",
        (event) => {
            if (
                isRecording &&
                activeButton === button
            ) {
                endHold(event);
            }
        }
    );

    button.addEventListener(
        "contextmenu",
        (event) => {
            event.preventDefault();
        }
    );
}


bindHoldButton(
    cameraAudioButton,
    true
);

bindHoldButton(
    audioOnlyButton,
    false
);

whiteboardButton.addEventListener(
    "click",
    openWhiteboard
);

whiteboardCloseButton.addEventListener(
    "click",
    closeWhiteboard
);

whiteboardOverlay.addEventListener(
    "pointerdown",
    (event) => {
        if (
            event.target ===
            whiteboardOverlay
        ) {
            closeWhiteboard();
        }
    }
);

whiteboardPanel.addEventListener(
    "pointerdown",
    (event) => {
        event.stopPropagation();
    }
);

beginButton.addEventListener(
    "click",
    beginTutor
);