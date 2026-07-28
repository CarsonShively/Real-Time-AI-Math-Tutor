const video = document.getElementById("camera");
const canvas = document.getElementById("capture-canvas");
const canvasContext = canvas.getContext("2d");

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

const correctStepsElement = document.getElementById(
    "correct-steps"
);

const incorrectStepElement = document.getElementById(
    "incorrect-step"
);

const tutorResponseElement = document.getElementById(
    "tutor-response"
);

const IMAGE_CAPTURE_DELAY_MS = 1000;

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

        cameraOffMessage.classList.add("hidden");

        updateButtons();
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

    activeButton.setPointerCapture(activePointerId);

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

    setCheckpoint("Listening");
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
        imageCaptureTimer = setTimeout(() => {
            if (isRecording) {
                imageCapturePromise =
                    captureImage();
            }
        }, IMAGE_CAPTURE_DELAY_MS);
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

    /*
     * If the user releases before one second,
     * take the silent image when the hold ends.
     */
    if (
        includeImageForTurn &&
        !imageCapturePromise
    ) {
        imageCapturePromise = captureImage();
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
        currentStream?.getAudioTracks() ?? [];

    audioTracks.forEach((track) => {
        track.enabled = false;
    });

    let imageBlob = null;

    if (includeImageForTurn) {
        imageBlob = imageCapturePromise
            ? await imageCapturePromise
            : capturedImageBlob;
    }

    audioChunks = [];
    imageCapturePromise = null;
    capturedImageBlob = null;
    mediaRecorder = null;
    activeButton = null;
    activePointerId = null;

    if (recordedAudioBlob.size === 0) {
        console.error(
            "The recorded audio was empty."
        );

        setCheckpoint("");
        updateButtons();
        return;
    }

    await handleCompletedTurn(
        recordedAudioBlob,
        imageBlob,
        includeImageForTurn
    );

    includeImageForTurn = false;
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
    updateButtons();

    const formData = new FormData();

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

        await readCheckpointStream(
            response,
            includedImage
        );
    } catch (error) {
        console.error(
            "Could not complete tutor turn:",
            error
        );

        setCheckpoint("Error");
    } finally {
        inferenceInProgress = false;
        updateButtons();
    }
}

async function readCheckpointStream(
    response,
    includedImage
) {
    if (!response.body) {
        throw new Error(
            "The response did not contain a stream."
        );
    }

    const reader =
        response.body.getReader();

    const decoder = new TextDecoder();

    let pendingText = "";
    let tutorResponse = null;
    let showUrl = "/show";
    let speakUrl = "/speak";

    while (true) {
        const {
            value,
            done,
        } = await reader.read();

        pendingText += decoder.decode(
            value || new Uint8Array(),
            {
                stream: !done,
            }
        );

        const lines = pendingText.split("\n");
        pendingText = lines.pop() ?? "";

        for (const line of lines) {
            const trimmedLine = line.trim();

            if (!trimmedLine) {
                continue;
            }

            const event = JSON.parse(
                trimmedLine
            );

            if (event.checkpoint) {
                setCheckpoint(
                    formatCheckpoint(
                        event.checkpoint
                    )
                );
            }

            tutorResponse =
                event.tutor_response ??
                event.response ??
                event.tutoring ??
                tutorResponse;

            showUrl =
                event.show_url ?? showUrl;

            speakUrl =
                event.speak_url ?? speakUrl;
        }

        if (done) {
            break;
        }
    }

    const finalLine = pendingText.trim();

    if (finalLine) {
        const event = JSON.parse(finalLine);

        if (event.checkpoint) {
            setCheckpoint(
                formatCheckpoint(
                    event.checkpoint
                )
            );
        }

        tutorResponse =
            event.tutor_response ??
            event.response ??
            event.tutoring ??
            tutorResponse;

        showUrl =
            event.show_url ?? showUrl;

        speakUrl =
            event.speak_url ?? speakUrl;
    }

    await updateWhiteboard(
        includedImage,
        tutorResponse,
        showUrl
    );

    await playTutorAudio(speakUrl);

    setCheckpoint("");
}

async function updateWhiteboard(
    includedImage,
    tutorResponse,
    showUrl
) {
    /*
     * For an audio-only turn, preserve the existing
     * steps and incorrect step. Only update the
     * tutor response.
     */
    if (includedImage) {
        try {
            const response = await fetch(
                showUrl,
                {
                    cache: "no-store",
                }
            );

            if (response.ok) {
                const data =
                    await response.json();

                const show =
                    data.show ?? data;

                renderCorrectSteps(
                    show?.correct_steps
                );

                renderIncorrectStep(
                    show?.first_user_incorrect_step
                );

                tutorResponse =
                    show?.tutor_response ??
                    show?.response ??
                    tutorResponse;
            }
        } catch (error) {
            console.error(
                "Could not update whiteboard work:",
                error
            );
        }
    }

    if (typeof tutorResponse === "string") {
        tutorResponseElement.textContent =
            tutorResponse;
    }
}

function renderCorrectSteps(steps) {
    correctStepsElement.innerHTML = "";

    if (!Array.isArray(steps)) {
        if (typeof steps === "string") {
            correctStepsElement.textContent =
                steps;
        }

        return;
    }

    for (const step of steps) {
        const stepElement =
            document.createElement("div");

        stepElement.className =
            "whiteboard-step";

        stepElement.textContent =
            String(step);

        correctStepsElement.appendChild(
            stepElement
        );
    }
}

function renderIncorrectStep(step) {
    if (
        step === null ||
        step === undefined ||
        step === ""
    ) {
        incorrectStepElement.textContent =
            "No incorrect step found.";
        return;
    }

    incorrectStepElement.textContent =
        String(step);
}

async function playTutorAudio(
    speakUrl = "/speak"
) {
    try {
        const response = await fetch(
            speakUrl,
            {
                cache: "no-store",
            }
        );

        if (!response.ok) {
            const errorText =
                await response.text();

            throw new Error(
                `Speech request failed: ` +
                `${response.status} ${errorText}`
            );
        }

        const audioBlob =
            await response.blob();

        const audioUrl =
            URL.createObjectURL(audioBlob);

        const audio = new Audio(audioUrl);

        audio.addEventListener(
            "ended",
            () => {
                URL.revokeObjectURL(audioUrl);
            },
            {
                once: true,
            }
        );

        audio.addEventListener(
            "error",
            () => {
                URL.revokeObjectURL(audioUrl);
            },
            {
                once: true,
            }
        );

        await audio.play();
    } catch (error) {
        console.error(
            "Could not play tutor audio:",
            error
        );
    }
}

function formatCheckpoint(checkpoint) {
    const normalized =
        String(checkpoint)
            .trim()
            .toLowerCase();

    const labels = {
        listening: "Listening",
        extracting: "Extracting",
        reasoning: "Reasoning",
        formatting: "Formatting",
        tutoring: "Tutoring",
        speaking: "Speaking",
        complete: "Complete",
    };

    return labels[normalized] ??
        normalized.charAt(0).toUpperCase() +
        normalized.slice(1);
}

function setCheckpoint(text) {
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

function openWhiteboard() {
    whiteboardOpen = true;

    whiteboardOverlay.classList.remove(
        "hidden"
    );

    whiteboardOverlay.setAttribute(
        "aria-hidden",
        "false"
    );

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
        activeButton === cameraAudioButton
    );

    audioOnlyButton.classList.toggle(
        "active",
        isRecording &&
        activeButton === audioOnlyButton
    );

    cameraAudioButton.setAttribute(
        "aria-pressed",
        String(
            isRecording &&
            activeButton === cameraAudioButton
        )
    );

    audioOnlyButton.setAttribute(
        "aria-pressed",
        String(
            isRecording &&
            activeButton === audioOnlyButton
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
            beginHold(event, includeImage);
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
        /*
         * Close only when the user presses outside
         * the whiteboard panel.
         */
        if (event.target === whiteboardOverlay) {
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

startMedia();