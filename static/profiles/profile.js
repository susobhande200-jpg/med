(function () {
  "use strict";

  const input = document.getElementById("id_avatar");
  const wrap = document.getElementById("profileAvatarPreviewWrap");
  if (!input || !wrap) return;

  let currentObjectUrl = null;
  const label = document.getElementById("profileAvatarPreviewLabel");
  const hint = document.getElementById("profileAvatarPreviewHint");

  input.addEventListener("change", function () {
    const file = input.files && input.files[0];
    if (!file) return;

    const allowedName = /\.(jpe?g|png|webp)$/i.test(file.name);
    const allowedType = ["image/jpeg", "image/png", "image/webp"].includes(file.type);
    if (!allowedName || (file.type && !allowedType)) {
      if (hint) hint.textContent = "Choose a genuine JPG, PNG or WebP image. The server will reject unsupported files.";
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      if (hint) hint.textContent = "This file is larger than 2 MB and will be rejected. Choose a smaller image.";
      return;
    }

    const previewUrl = URL.createObjectURL(file);
    let preview = wrap.querySelector("[data-profile-preview]");
    if (!preview) {
      preview = document.createElement("img");
      preview.className = "pr-avatar";
      preview.dataset.profilePreview = "true";
      preview.alt = "Selected profile picture preview";
      const fallback = document.getElementById("profileAvatarFallback");
      if (fallback) fallback.remove();
      wrap.insertBefore(preview, wrap.firstElementChild);
    }
    if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl);
    currentObjectUrl = previewUrl;
    preview.src = previewUrl;
    preview.alt = "Selected profile picture preview";
    if (label) label.textContent = "Selected picture preview";
    if (hint) hint.textContent = "Preview only. Select Save changes below to upload this picture.";
  });

  window.addEventListener("beforeunload", function () {
    if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl);
  });
})();
