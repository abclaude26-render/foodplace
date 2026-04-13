// The Golden Lantern — main.js
// Flash auto-dismiss
setTimeout(() => {
  document.querySelectorAll('.flash').forEach(f => f.remove());
}, 5000);
