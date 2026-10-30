/* Smart Document Manager - Camera Scanner and OCR Uploader */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const video = $("cameraVideo");
  const canvas = $("previewCanvas");
  const ctx = canvas ? canvas.getContext("2d") : null;

  const state = {
    stream: null,
    facingMode: "environment",
    rotation: 0,
    sourceImage: null,
    sourceFile: null
  };

  // Show alerts
  function showAlert(title, message, type = "info") {
    const box = $("cameraAlertBox");

    if (!box) {
      window.alert(`${title}\n${message}`);
      return;
    }

    box.className = `alert alert-${type} mb-4 shadow-sm`;

    if ($("cameraAlertTitle")) {
      $("cameraAlertTitle").textContent = title;
    }

    if ($("cameraAlertMessage")) {
      $("cameraAlertMessage").textContent = message;
    }

    const icon = $("cameraAlertIcon");

    if (icon) {
      icon.className =
        `bi ${type === "danger"
          ? "bi-exclamation-triangle-fill"
          : "bi-info-circle-fill"} fs-5 mt-1`;
    }

    box.classList.remove("d-none");
  }

  function hideAlert() {
    $("cameraAlertBox")?.classList.add("d-none");
  }

  // Camera requires HTTPS or localhost
  function secureCameraAllowed() {
    return window.isSecureContext === true ||
      ["localhost", "127.0.0.1", "::1"]
        .includes(window.location.hostname);
  }

  // Stop the camera
  function stopCamera() {
    if (state.stream) {
      state.stream.getTracks().forEach(track => track.stop());
    }

    state.stream = null;

    if (video) {
      video.srcObject = null;
    }

    $("cameraIdleOverlay")?.classList.remove("d-none");
    $("startCameraBtn")?.classList.remove("d-none");
    $("capturePhotoBtn")?.classList.add("d-none");
    $("switchCameraBtn")?.classList.add("d-none");
    $("stopCameraBtn")?.classList.add("d-none");
  }

  // Start live camera
  async function startCamera() {
    hideAlert();

    if (
      !navigator.mediaDevices ||
      !navigator.mediaDevices.getUserMedia ||
      !secureCameraAllowed()
    ) {
      showAlert(
        "Live camera is blocked",
        "Open http://127.0.0.1:5000 on this computer, or run " +
        "`python app.py --https` for HTTPS access. " +
        "You can also take a photo using your phone camera or upload an image.",
        "warning"
      );
      return;
    }

    stopCamera();

    try {
      state.stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: { ideal: state.facingMode },
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        }
      });

      video.srcObject = state.stream;
      await video.play();

      $("cameraIdleOverlay")?.classList.add("d-none");
      $("startCameraBtn")?.classList.add("d-none");
      $("capturePhotoBtn")?.classList.remove("d-none");
      $("switchCameraBtn")?.classList.remove("d-none");
      $("stopCameraBtn")?.classList.remove("d-none");

      $("cameraSection")?.classList.remove("d-none");
      $("cameraControlsArea")?.classList.remove("d-none");
      $("previewSection")?.classList.add("d-none");

    } catch (error) {
      let message = "Allow camera permission and try again.";

      if (error.name === "NotAllowedError") {
        message = "Camera permission denied. Allow camera access in browser settings.";
      } else if (error.name === "NotFoundError") {
        message = "No camera found. Use your phone camera or upload an image.";
      } else if (error.name === "NotReadableError") {
        message = "Camera may be in use by another application.";
      }

      showAlert("Unable to start camera", message, "warning");
      stopCamera();
    }
  }

  // Draw and adjust the captured image
  function drawPreview() {
    if (!ctx || !canvas || !state.sourceImage) return;

    const brightness = Number($("brightnessSlider")?.value || 100);
    const contrast = Number($("contrastSlider")?.value || 100);
    const image = state.sourceImage;

    const width =
      image.videoWidth || image.naturalWidth || image.width;
    const height =
      image.videoHeight || image.naturalHeight || image.height;

    if (!width || !height) return;

    const rotated = Math.abs(state.rotation % 180) === 90;

    canvas.width = rotated ? height : width;
    canvas.height = rotated ? width : height;

    ctx.save();
    ctx.filter =
      `brightness(${brightness}%) contrast(${contrast}%)`;

    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate(state.rotation * Math.PI / 180);

    ctx.drawImage(
      image,
      -width / 2,
      -height / 2,
      width,
      height
    );

    ctx.restore();

    $("previewSection")?.classList.remove("d-none");
    $("cameraSection")?.classList.add("d-none");
    $("cameraControlsArea")?.classList.add("d-none");
  }

  // Display a captured or uploaded image
  function showCapturedImage(image, file = null) {
    state.sourceImage = image;
    state.sourceFile = file;
    state.rotation = 0;

    if ($("brightnessSlider")) {
      $("brightnessSlider").value = 100;
    }

    if ($("contrastSlider")) {
      $("contrastSlider").value = 100;
    }

    if ($("brightnessVal")) {
      $("brightnessVal").textContent = "100%";
    }

    if ($("contrastVal")) {
      $("contrastVal").textContent = "100%";
    }

    drawPreview();
  }

  // Capture a photo from the live camera
  function capturePhoto() {
    if (!video || !video.videoWidth) {
      showAlert(
        "Camera not ready",
        "Wait for the camera preview before capturing.",
        "warning"
      );
      return;
    }

    const shot = document.createElement("canvas");
    shot.width = video.videoWidth;
    shot.height = video.videoHeight;

    shot.getContext("2d").drawImage(
      video, 0, 0, shot.width, shot.height
    );

    const image = new Image();

    image.onload = () => {
      stopCamera();
      showCapturedImage(image);
    };

    image.src = shot.toDataURL("image/jpeg", 0.92);
  }

  // Open and validate an uploaded image
  function imageFromFile(file) {
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      showAlert(
        "Unsupported file",
        "Please select a JPG, PNG, or supported image.",
        "danger"
      );
      return;
    }

    if (file.size > 15 * 1024 * 1024) {
      showAlert(
        "Image too large",
        "Please select an image smaller than 15 MB.",
        "danger"
      );
      return;
    }

    const image = new Image();
    const imageURL = URL.createObjectURL(file);

    image.onload = () => {
      URL.revokeObjectURL(imageURL);
      stopCamera();
      showCapturedImage(image, file);
    };

    image.onerror = () => {
      URL.revokeObjectURL(imageURL);

      showAlert(
        "Unable to open image",
        "Please choose another image.",
        "danger"
      );
    };

    image.src = imageURL;
  }

  // Convert the preview to an image file
  function canvasToBlob(targetCanvas) {
    return new Promise((resolve, reject) => {
      targetCanvas.toBlob(
        blob => blob
          ? resolve(blob)
          : reject(new Error("Unable to prepare image.")),
        "image/jpeg",
        0.92
      );
    });
  }

  // Send the image to Flask OCR endpoint
  async function runOCR() {
    if (!canvas || !canvas.width || !canvas.height) {
      showAlert(
        "No image selected",
        "Capture a photo or upload an image first.",
        "warning"
      );
      return;
    }

    const button = $("usePhotoBtn");
    const spinner = $("ocrSpinner");

    if (button) button.disabled = true;
    spinner?.classList.remove("d-none");

    try {
      const blob = await canvasToBlob(canvas);

      const file = new File(
        [blob],
        "document-scan.jpg",
        { type: "image/jpeg" }
      );

      const data = new FormData();
      data.append("image", file);

      const csrf = document.querySelector(
        'input[name="csrf_token"]'
      )?.value;

      const headers = csrf
        ? { "X-CSRFToken": csrf }
        : {};

      const response = await fetch("/api/ocr-process", {
        method: "POST",
        body: data,
        headers,
        credentials: "same-origin"
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(
          result.message || "OCR processing failed."
        );
      }

      // Fill hidden upload information
      if ($("formTempFilename")) {
        $("formTempFilename").value =
          result.temp_filename || "";
      }

      if ($("formOrigFilename")) {
        $("formOrigFilename").value =
          result.original_filename || file.name;
      }

      if ($("formFileSize")) {
        $("formFileSize").value =
          result.file_size || blob.size;
      }

      if ($("formMimeType")) {
        $("formMimeType").value =
          result.mime_type || blob.type;
      }

      // Fill fields using extracted OCR data
      const extracted = result.extracted || {};

      function fillField(id, ...keys) {
        const element = $(id);
        if (!element) return;

        for (const key of keys) {
          const value = extracted[key];

          if (
            value !== undefined &&
            value !== null &&
            String(value).trim()
          ) {
            element.value = String(value);
            return;
          }
        }
      }

      fillField("formTitle",
        "title", "document_title", "document_type", "type");

      fillField("formCategory",
        "category", "category_key");

      fillField("formDocNumber",
        "document_number", "id_number", "number",
        "identity_number");

      fillField("formHolderName",
        "holder_name", "name", "applicant_name");

      fillField("formAuthority",
        "issuing_authority", "authority", "issuer");

      fillField("formIssueDate", "issue_date");

      fillField("formExpiryDate",
        "expiry_date", "expiration_date");

      fillField("formNotes", "notes");

      // Display OCR output
      if ($("rawOcrText")) {
        $("rawOcrText").textContent =
          result.raw_text ||
          "No readable text detected. Enter details manually.";
      }

      if ($("ocrNotice")) {
        $("ocrNotice").textContent =
          result.tesseract_available
            ? "OCR finished. Verify all extracted details before saving."
            : "OCR engine unavailable. Enter document details manually.";

        $("ocrNotice").className =
          `alert py-2 small mb-3 shadow-sm ${
            result.tesseract_available
              ? "alert-success"
              : "alert-warning"
          }`;
      }

      $("ocrReviewSection")?.classList.remove("d-none");
      $("ocrWaitingPlaceholder")?.classList.add("d-none");

      showAlert(
        "Image processed",
        result.message ||
          "Review the extracted details before saving.",
        "success"
      );

    } catch (error) {
      showAlert(
        "OCR processing failed",
        error.message || "Check the connection and try again.",
        "danger"
      );

    } finally {
      if (button) button.disabled = false;
      spinner?.classList.add("d-none");
    }
  }

  // Button events
  $("startCameraBtn")?.addEventListener(
    "click", startCamera
  );

  $("capturePhotoBtn")?.addEventListener(
    "click", capturePhoto
  );

  $("stopCameraBtn")?.addEventListener(
    "click", stopCamera
  );

  $("switchCameraBtn")?.addEventListener(
    "click",
    async () => {
      state.facingMode =
        state.facingMode === "environment"
          ? "user"
          : "environment";

      await startCamera();
    }
  );

  // Phone native camera
  $("nativeCameraBtn")?.addEventListener(
    "click",
    () => $("nativeCameraInput")?.click()
  );

  $("nativeCameraInput")?.addEventListener(
    "change",
    event => {
      imageFromFile(event.target.files?.[0]);
      event.target.value = "";
    }
  );

  // Image upload
  $("fileUploadInput")?.addEventListener(
    "change",
    event => {
      imageFromFile(event.target.files?.[0]);
      event.target.value = "";
    }
  );

  // Retake photo
  $("retakePhotoBtn")?.addEventListener(
    "click",
    () => {
      state.sourceImage = null;
      state.sourceFile = null;
      state.rotation = 0;

      $("previewSection")?.classList.add("d-none");
      $("cameraSection")?.classList.remove("d-none");
      $("cameraControlsArea")?.classList.remove("d-none");
      $("cameraIdleOverlay")?.classList.remove("d-none");

      $("startCameraBtn")?.classList.remove("d-none");
      $("capturePhotoBtn")?.classList.add("d-none");
      $("switchCameraBtn")?.classList.add("d-none");
      $("stopCameraBtn")?.classList.add("d-none");
    }
  );

  // Process captured image
  $("usePhotoBtn")?.addEventListener(
    "click", runOCR
  );

  // Rotate image
  $("rotateBtn")?.addEventListener(
    "click",
    () => {
      state.rotation = (state.rotation + 90) % 360;
      drawPreview();
    }
  );

  // Reset image adjustments
  $("resetFiltersBtn")?.addEventListener(
    "click",
    () => {
      state.rotation = 0;

      if ($("brightnessSlider")) {
        $("brightnessSlider").value = 100;
      }

      if ($("contrastSlider")) {
        $("contrastSlider").value = 100;
      }

      if ($("brightnessVal")) {
        $("brightnessVal").textContent = "100%";
      }

      if ($("contrastVal")) {
        $("contrastVal").textContent = "100%";
      }

      drawPreview();
    }
  );

  // Brightness and contrast controls
  $("brightnessSlider")?.addEventListener(
    "input",
    () => {
      if ($("brightnessVal")) {
        $("brightnessVal").textContent =
          `${$("brightnessSlider").value}%`;
      }

      drawPreview();
    }
  );

  $("contrastSlider")?.addEventListener(
    "input",
    () => {
      if ($("contrastVal")) {
        $("contrastVal").textContent =
          `${$("contrastSlider").value}%`;
      }

      drawPreview();
    }
  );

  // Always release camera when leaving the page
  window.addEventListener("pagehide", stopCamera);

  // Explain HTTP camera restrictions
  if (!secureCameraAllowed()) {
    showAlert(
      "HTTP security restriction detected",
      "Live webcam video may be blocked at this network address. " +
      "Use Open Phone Camera or Upload Image, open this app at " +
      "http://127.0.0.1:5000 on your computer, or run " +
      "`python app.py --https` for HTTPS access.",
      "warning"
    );
  }
})();