const picker = document.getElementById("origin-profile-select");
const panel = document.getElementById("origin-selected-profile");
const status = document.getElementById("origin-profile-status");
const image = document.getElementById("origin-selected-image");
image.loading = "eager"; // Only the selected image gets a source URL.
let requestNumber = 0;

picker.addEventListener("change", () => {
  const option = picker.selectedOptions[0];
  requestNumber += 1;
  const current = requestNumber;
  if (!option?.value) {
    panel.hidden = true;
    image.removeAttribute("src");
    status.textContent = "Choose an origin to display its profile.";
    return;
  }
  const name = option.dataset.profileName;
  const source = option.dataset.profileSrc;
  document.getElementById("origin-selected-title").textContent = name + " (" + option.value + ")";
  image.alt = name + ": receiving-country shares of applications and recognised decisions, with percentage-point differences, 2000–2025.";
  status.textContent = "Loading the profile for " + name + "...";
  image.hidden = true;
  image.onload = () => {
    if (current === requestNumber) {
      image.hidden = false;
      status.textContent = "Showing " + name + ". Select another origin to compare profiles.";
    }
  };
  image.onerror = () => {
    if (current === requestNumber) status.textContent = "The profile for " + name + " could not be loaded. Please try again.";
  };
  for (const id of ["origin-selected-image-link", "origin-selected-full", "origin-selected-download"]) {
    document.getElementById(id).href = source;
  }
  document.getElementById("origin-selected-download").download = option.value + "-origin-profile.png";
  panel.hidden = false;
  image.src = source;
  if (image.complete && image.naturalWidth > 0) image.onload();
});
