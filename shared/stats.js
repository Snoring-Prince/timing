// Shared by investor profiles and the two comparison tools.
(() => {
  if (['localhost', '127.0.0.1', '[::1]', ''].includes(location.hostname)) return;
  try {
    if (localStorage.getItem('umami.disabled')) return;
  } catch {
    // Browsers with unavailable storage can still use the site.
  }

  const script = document.createElement('script');
  script.async = true;
  script.src = 'https://cloud.umami.is/script.js';
  script.setAttribute('data-website-id', '41e07a57-a87c-403b-bdf8-e12d911457b6');
  document.head.appendChild(script);

  window.track = (name, data) => {
    try {
      window.umami?.track(name, data);
    } catch {
      // Analytics failures must not interrupt the comparison.
    }
  };
})();
