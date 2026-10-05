/* gallery-link.js — a small "← Gallery" pill, fixed in the bottom-left corner, linking back to the dataviz gallery.
   Include once, near the end of <body>, from any page one folder below the repository root:
       <script src="../gallery-link.js" defer></script>
   One file controls the look and the text for every page. It stays out of the way of page headers, picks a dark or a
   light pill from the page's own background color, and is hidden when the page is embedded in another page or printed. */
(function () {
  if (window.self !== window.top) return;                       // embedded somewhere: the host page has its own navigation
  var href = document.currentScript && document.currentScript.src ? new URL("./", document.currentScript.src).href : "../";
  var a = document.createElement("a");
  a.href = href; a.textContent = "← Gallery"; a.title = "All dashboards"; a.className = "gallery-link";
  // light or dark pill, decided from the page's own background (so it reads on the cream planners and the white maps too);
  // re-decided when the page switches theme (a data-theme / class change on <html> or <body>, or the system setting)
  var css = document.createElement("style");
  function paint() {
    var bg = getComputedStyle(document.body).backgroundColor.match(/\d+/g) || [20, 24, 28];
    var light = (0.2126 * bg[0] + 0.7152 * bg[1] + 0.0722 * bg[2]) > 140;
    css.textContent =
      ".gallery-link{position:fixed;left:14px;bottom:14px;z-index:9999;display:inline-flex;align-items:center;gap:6px;" +
      "padding:5px 12px;border-radius:999px;font:600 12px/1.3 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;" +
      "text-decoration:none;box-shadow:0 2px 8px rgba(0,0,0,.2);opacity:.85;transition:opacity .15s,color .15s,border-color .15s;" +
      (light ? "color:#4a5a6a;background:rgba(255,255,255,.92);border:1px solid #c9d1da}" : "color:#9ab;background:rgba(20,24,28,.92);border:1px solid #384352}") +
      ".gallery-link:hover{opacity:1;color:" + (light ? "#00913a" : "#00e054") + ";border-color:#00a83f}" +
      "@media print{.gallery-link{display:none}}" +
      "@media (max-width:600px){.gallery-link{left:10px;bottom:10px;padding:4px 10px;font-size:11px}}";
  }
  paint();
  document.head.appendChild(css);
  new MutationObserver(paint).observe(document.documentElement, { attributes: true, attributeFilter: ["class", "data-theme", "style"] });
  new MutationObserver(paint).observe(document.body, { attributes: true, attributeFilter: ["class", "data-theme", "style"] });
  if (window.matchMedia) matchMedia("(prefers-color-scheme: dark)").addEventListener("change", paint);
  document.body.appendChild(a);
})();
