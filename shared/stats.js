// Shared by investor profiles and the two comparison tools.
(() => {
  if (['localhost', '127.0.0.1', '[::1]', ''].includes(location.hostname)) return;
  try {
    if (localStorage.getItem('umami.disabled')) return;
  } catch {
    // Browsers with unavailable storage can still use the site.
  }

  // Clicks made while Umami is still loading used to be dropped: on the Olympics page
  // the first character, result and comparison clicks often came before it was ready
  // (2026-11-23 review). They now wait here and are sent once, in order, on load.
  // A blocked or failed script sends nothing, and the queue never grows past a few.
  const waiting = [];
  let failed = false;
  const send = (name, data) => {
    try {
      window.umami.track(name, data);
    } catch {
      // Analytics failures must not interrupt the comparison.
    }
  };

  const script = document.createElement('script');
  script.async = true;
  script.src = 'https://cloud.umami.is/script.js';
  script.setAttribute('data-website-id', '41e07a57-a87c-403b-bdf8-e12d911457b6');
  script.addEventListener('load', () => {
    for (const [name, data] of waiting.splice(0)) send(name, data);
  });
  script.addEventListener('error', () => {
    failed = true;
    waiting.length = 0;
  });
  document.head.appendChild(script);

  window.track = (name, data) => {
    if (typeof window.umami?.track === 'function') send(name, data);
    else if (!failed && waiting.length < 20) waiting.push([name, data]);
  };
})();
