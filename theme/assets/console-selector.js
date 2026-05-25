/**
 * Cartridge Club — console selector.
 *
 * Persists the chosen console as a `console_id` cookie and `?console=`
 * URL param. Reload the page on change so server-side Liquid sees the new
 * value (Section Rendering API could swap this out for partial reloads).
 */
(function () {
  const COOKIE = 'console_id';
  const PARAM = 'console';

  function readCookie(name) {
    return document.cookie
      .split('; ')
      .map(c => c.split('='))
      .reduce((acc, [k, v]) => (k === name ? decodeURIComponent(v) : acc), '');
  }

  function writeCookie(name, value) {
    const oneYear = 60 * 60 * 24 * 365;
    document.cookie = `${name}=${encodeURIComponent(value)}; max-age=${oneYear}; path=/; samesite=lax`;
  }

  function currentSelection() {
    const url = new URL(window.location.href);
    return url.searchParams.get(PARAM) || readCookie(COOKIE) || '';
  }

  function applySelection(select) {
    const value = currentSelection();
    if (value && [...select.options].some(o => o.value === value)) {
      select.value = value;
    }
  }

  function navigateTo(value) {
    const url = new URL(window.location.href);
    if (value) {
      url.searchParams.set(PARAM, value);
      writeCookie(COOKIE, value);
    } else {
      url.searchParams.delete(PARAM);
      writeCookie(COOKIE, '');
    }
    window.location.href = url.toString();
  }

  document.querySelectorAll('[data-cc-console-select]').forEach(select => {
    applySelection(select);
    select.addEventListener('change', e => navigateTo(e.target.value));
  });
})();
