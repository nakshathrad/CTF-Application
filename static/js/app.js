/* GuardianMart — app.js
 *
 * Two things live here, both deliberate:
 *
 *  1. validateClaimUpload() — the ONLY file-type check in the whole
 *     application (A08). The server accepts anything. Removing the
 *     accept attribute, or just disabling JavaScript, bypasses this
 *     entirely — which is the point: client-side validation is UX,
 *     not a security control.
 *
 *  2. An alert() detector used to score the stored-XSS challenge
 *     (A05b). Nothing here executes a payload — the payload runs on
 *     its own because /support/admin renders ticket text with |safe.
 *     This only *notices* that it ran, and reveals the flag that the
 *     server already sent down with the page. Simulation, not impact.
 */

(function () {
  "use strict";

  window.__gm_alert_fired = false;

  function revealXssFlag() {
    var box = document.getElementById("xss-flag-box");
    if (box) {
      box.style.display = "block";
    }
  }

  // Wrap alert() rather than replacing it, so the popup the player
  // expects to see still appears.
  var nativeAlert = window.alert;
  window.alert = function () {
    window.__gm_alert_fired = true;
    revealXssFlag();
    return nativeAlert.apply(window, arguments);
  };

  // A payload firing mid-parse may run before the flag box exists in
  // the DOM, so check again once the document has finished loading.
  document.addEventListener("DOMContentLoaded", function () {
    if (window.__gm_alert_fired) {
      revealXssFlag();
    }
  });
})();

/* A08 — client-side-only claim upload validation. */
function validateClaimUpload(form) {
  var input = form.querySelector('input[type="file"]');
  if (!input || !input.files || input.files.length === 0) {
    alert("Please choose a claim document to upload.");
    return false;
  }
  var name = input.files[0].name.toLowerCase();
  if (name.slice(-4) !== ".pdf") {
    alert("Only PDF claim documents are accepted.");
    return false;
  }
  return true;
}
