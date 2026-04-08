/**
 * Live HLS helper for Liquidsoap harbor (single-variant TS). Handles fatal
 * bufferAppendError / "SourceBuffer does not exist" by recoverMediaError,
 * then full teardown + reload (common when input clips change codec params).
 */
(function () {
  var HLS_SRC = "https://cdn.jsdelivr.net/npm/hls.js@1.5.18";

  function defaultConfig(extra) {
    var o = {
      enableWorker: false,
      lowLatencyMode: false,
      liveBackBufferLength: 90,
      maxBufferLength: 120,
      maxBufferHole: 0.5,
      maxSeekHole: 2,
      manifestLoadingTimeOut: 20000,
      levelLoadingTimeOut: 20000,
      fragLoadingTimeOut: 20000,
    };
    if (extra && typeof extra === "object") {
      for (var k in extra) if (Object.prototype.hasOwnProperty.call(extra, k)) o[k] = extra[k];
    }
    return o;
  }

  window.GlcLiveHls = {
    /**
     * @param {HTMLVideoElement} el
     * @param {string} manifestUrl e.g. /hls/live.m3u8
     * @param {object} [options] { hls: {...} } merged into Hls config
     */
    attach: function (el, manifestUrl, options) {
      if (!el || el.dataset.glcHlsBound === "1") return;
      el.dataset.glcHlsBound = "1";
      options = options || {};

      function tryNative() {
        if (el.canPlayType("application/vnd.apple.mpegurl")) {
          el.src = manifestUrl;
          return true;
        }
        return false;
      }

      function run() {
        if (!window.Hls || !Hls.isSupported()) {
          if (!tryNative()) {
            el.insertAdjacentHTML(
              "afterend",
              '<p class="glc-hls-fallback-msg" style="margin:0;font-size:0.75rem;color:#9aa8a0;">HLS needs Safari or hls.js. <a href="' +
                manifestUrl +
                '">Open manifest</a>.</p>'
            );
          }
          return;
        }

        var hlsInstance = null;
        var fullResetCount = 0;
        var maxFullResets = 14;

        function destroyHls() {
          if (hlsInstance) {
            try {
              hlsInstance.destroy();
            } catch (e) {}
            hlsInstance = null;
          }
        }

        function hardResetVideo() {
          try {
            el.pause();
          } catch (e) {}
          try {
            el.removeAttribute("src");
            el.load();
          } catch (e) {}
        }

        function createHls() {
          destroyHls();
          var mediaErrTries = 0;
          var hls = new Hls(defaultConfig(options.hls));
          hlsInstance = hls;
          hls.loadSource(manifestUrl);
          hls.attachMedia(el);

          hls.on(Hls.Events.FRAG_BUFFERED, function () {
            fullResetCount = 0;
          });

          hls.on(Hls.Events.ERROR, function (_, data) {
            if (!data.fatal) return;
            console.warn("[GlcLiveHls] fatal:", data.type, data.details, data);

            if (data.type === Hls.ErrorTypes.MEDIA_ERROR && mediaErrTries < 2) {
              mediaErrTries++;
              try {
                hls.recoverMediaError();
                return;
              } catch (e) {
                /* fall through */
              }
            }

            if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
              try {
                hls.startLoad();
                return;
              } catch (e) {
                /* fall through */
              }
            }

            if (fullResetCount >= maxFullResets) {
              console.error("[GlcLiveHls] too many full resets; stop retrying.");
              return;
            }
            fullResetCount++;
            destroyHls();
            hardResetVideo();
            var delay = Math.min(10000, 350 + fullResetCount * 350);
            setTimeout(createHls, delay);
          });
        }

        createHls();
      }

      if (window.Hls) run();
      else {
        var s = document.createElement("script");
        s.src = HLS_SRC;
        s.async = true;
        s.onload = run;
        s.onerror = function () {
          tryNative();
        };
        document.head.appendChild(s);
      }
    },
  };
})();
