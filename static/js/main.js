/* FITNESS ZONE: progressive enhancements. Every feature works without JavaScript.
   Success animations only run after the server confirms (Django messages / JSON replies).
   Nothing sensitive (passwords, tokens) is ever stored in the browser. */
(function () {
  "use strict";
  var doc = document, root = doc.documentElement;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $ = function (s, c) { return (c || doc).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || doc).querySelectorAll(s)); };
  var store = {
    get: function (k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { window.localStorage.setItem(k, v); } catch (e) {} },
    sget: function (k) { try { return window.sessionStorage.getItem(k); } catch (e) { return null; } },
    sset: function (k, v) { try { window.sessionStorage.setItem(k, v); } catch (e) {} }
  };

  /* ---------- mobile nav ---------- */
  var toggle = $(".nav-toggle"), nav = $("#site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  /* ---------- opening animation: skip, remember, never block ---------- */
  var intro = $("#intro");
  function endIntro() {
    root.classList.remove("intro-on");
    store.set("fz_intro_seen", "1");
  }
  if (intro && root.classList.contains("intro-on")) {
    var skip = $(".intro-skip", intro);
    if (skip) skip.addEventListener("click", endIntro);
    doc.addEventListener("keydown", function (e) { if (e.key === "Escape") endIntro(); });
    window.setTimeout(endIntro, 6200); // CSS hides it at ~6s even if this never runs
  }

  /* ---------- scroll reveal ---------- */
  var reveals = $$(".reveal");
  if (reveals.length) {
    if (!("IntersectionObserver" in window) || reduce) {
      reveals.forEach(function (el) { el.classList.add("in"); });
    } else {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
      }, { threshold: .12 });
      reveals.forEach(function (el) { io.observe(el); });
    }
  }

  /* ---------- toasts from Django messages ---------- */
  $$(".toast").forEach(function (t) {
    var close = function () { t.classList.add("out"); window.setTimeout(function () { t.remove(); }, 260); };
    var b = $("button", t); if (b) b.addEventListener("click", close);
    window.setTimeout(close, 7000);
  });

  /* ---------- sorting applies immediately ---------- */
  $$("[data-autosubmit]").forEach(function (el) {
    el.addEventListener("change", function () { if (el.form) el.form.submit(); });
  });

  /* ---------- cart count bump when it changes ---------- */
  var cartCount = $("[data-cart-count]");
  if (cartCount) {
    var now = parseInt(cartCount.textContent, 10) || 0, before = store.sget("fz_cart");
    if (before !== null && parseInt(before, 10) !== now && !reduce) cartCount.classList.add("bump");
    store.sset("fz_cart", String(now));
  } else {
    store.sset("fz_cart", "0");
  }

  /* ---------- favourites: toggle without reload (animation after server confirms) ---------- */
  var favCount = $("[data-fav-count]");
  doc.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form.matches || !form.matches(".fav-form, .fav-form-inline")) return;
    event.preventDefault();
    var btn = $(".fav-btn", form);
    btn.disabled = true;
    fetch(form.action, { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" }, body: new FormData(form), credentials: "same-origin" })
      .then(function (res) { return res.json().then(function (data) { return { status: res.status, data: data }; }); })
      .then(function (r) {
        if (r.status === 401 && r.data.login) { window.location.href = r.data.login; return; }
        btn.classList.toggle("is-on", r.data.favourited);
        btn.setAttribute("aria-pressed", r.data.favourited ? "true" : "false");
        if (!reduce) { btn.classList.remove("pop"); void btn.offsetWidth; btn.classList.add("pop"); }
        var label = $("[data-fav-label]", btn);
        if (label) label.textContent = r.data.favourited ? "Saved to favourites" : "Save to favourites";
        if (favCount) { favCount.textContent = r.data.count; favCount.hidden = !r.data.count; if (!reduce) { favCount.classList.remove("bump"); void favCount.offsetWidth; favCount.classList.add("bump"); } }
        btn.disabled = false;
      })
      .catch(function () { form.submit(); });
  });

  /* ---------- password visibility + strength ---------- */
  $$("[data-toggle-password]").forEach(function (b) {
    b.addEventListener("click", function () {
      var input = $("input", b.parentNode);
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      b.textContent = show ? "Hide" : "Show";
      b.setAttribute("aria-pressed", show ? "true" : "false");
    });
  });
  var pw1 = $("#id_password1"), meter = $("[data-meter]");
  if (pw1 && meter) {
    var bar = $("span", meter), label = $("[data-meter-label]");
    pw1.addEventListener("input", function () {
      var v = pw1.value, score = 0;
      if (v.length >= 8) score++; if (v.length >= 12) score++;
      if (/[a-z]/.test(v) && /[A-Z]/.test(v)) score++;
      if (/\d/.test(v)) score++; if (/[^A-Za-z0-9]/.test(v)) score++;
      var pct = v ? Math.max(12, score * 20) : 0;
      bar.style.width = pct + "%";
      bar.style.background = score <= 1 ? "#ff7b6b" : score <= 3 ? "#ffd166" : "#b7ff45";
      if (label) label.textContent = !v ? "" : score <= 1 ? "Weak: try a longer password" : score <= 3 ? "Getting there" : "Strong";
    });
  }

  /* ---------- loading state on submit (shows progress only; success comes from the server) ---------- */
  $$("form[data-loading]").forEach(function (f) {
    f.addEventListener("submit", function () {
      var b = $("button[type=submit]", f);
      if (b && !b.disabled) { b.setAttribute("aria-busy", "true"); b.dataset.label = b.textContent; b.textContent = f.dataset.loading; window.setTimeout(function () { b.disabled = true; }, 0); }
    });
  });

  /* ---------- Forge Buddy ---------- */
  var buddy = $("#buddy");
  if (buddy) {
    if (store.sget("fz_buddy_off") === "1") { buddy.hidden = true; }
    var msg = $("[data-buddy-msg]", buddy);
    var say = function (t) { if (!msg || buddy.hidden) return; msg.textContent = t; var bub = $(".buddy-bubble", buddy); if (bub && !reduce) { bub.style.animation = "none"; void bub.offsetWidth; bub.style.animation = ""; } };
    $(".buddy-close", buddy).addEventListener("click", function () { buddy.hidden = true; store.sset("fz_buddy_off", "1"); });
    var pwField = $("input[type=password]");
    if (pwField) pwField.addEventListener("focus", function () { say("One step at a time, champion."); });
    var form = $("form[data-buddy-submit]");
    if (form) form.addEventListener("submit", function () { say(form.dataset.buddySubmit); });
  }

  /* ---------- gear finder (builds a real shop link, no fake results) ---------- */
  var finder = $("#gear-finder");
  if (finder) {
    var tips = {
      "strength-weights": "Start with one adjustable dumbbell set or a kettlebell. You don't need a full rack to build strength.",
      "cardio-conditioning": "A skipping rope and a resistance band set cover a lot of ground for very little money.",
      "yoga-recovery": "A good mat and a foam roller are enough for stretching, mobility and recovery.",
      "cricket": "Match your bat size to your height, and buy protective gear before anything fancy.",
      "badminton-racket-sports": "A mid-range racket and a pack of shuttles is all you need to begin.",
      "footwear-apparel": "Comfortable, well-fitting shoes matter more than brand.",
      "gym-accessories": "Gloves, a bottle and a bag are useful, but optional on day one."
    };
    var out = $("[data-finder-out]", finder), link = $("[data-finder-link]", finder), tip = $("[data-finder-tip]", finder);
    var update = function () {
      var cat = $("[name=cat]", finder).value, budget = $("[name=budget]", finder).value;
      var qs = "?category=" + encodeURIComponent(cat) + "&in_stock=1" + (budget ? "&max_price=" + encodeURIComponent(budget) : "");
      link.href = finder.dataset.shop + qs;
      tip.textContent = tips[cat] || "";
      out.hidden = false;
    };
    $$("select", finder).forEach(function (s) { s.addEventListener("change", update); });
    update();
  }

  /* ---------- workout tracker progress ---------- */
  var tracker = $("[data-tracker]");
  if (tracker) {
    var boxes = $$("input[type=checkbox]", tracker), fill = $("[data-progress-fill]"), txt = $("[data-progress-text]");
    var refresh = function () {
      var done = boxes.filter(function (b) { return b.checked; }).length;
      var pct = boxes.length ? Math.round(done / boxes.length * 100) : 0;
      if (fill) fill.style.width = pct + "%";
      if (txt) txt.textContent = done + " of " + boxes.length + " sets ticked";
    };
    boxes.forEach(function (b) { b.addEventListener("change", refresh); });
    refresh();
  }

  /* ---------- dashboard weight chart (inline SVG) ---------- */
  var chart = $("#weight-chart"), dataEl = $("#weight-data");
  if (chart && dataEl) {
    var points = JSON.parse(dataEl.textContent || "[]");
    if (points.length < 2) {
      chart.innerHTML = '<p class="empty-chart">Add two or more weight entries to see your trend.</p>';
    } else {
      var W = 320, H = 140, P = 22;
      var vals = points.map(function (p) { return p.kg; });
      var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
      if (hi === lo) { hi += 1; lo -= 1; }
      var x = function (i) { return P + (W - 2 * P) * i / (points.length - 1); };
      var y = function (v) { return H - P - (H - 2 * P) * (v - lo) / (hi - lo); };
      var line = points.map(function (p, i) { return (i ? "L" : "M") + x(i).toFixed(1) + " " + y(p.kg).toFixed(1); }).join(" ");
      var dots = points.map(function (p, i) { return '<circle cx="' + x(i).toFixed(1) + '" cy="' + y(p.kg).toFixed(1) + '" r="3.5" fill="#b7ff45"><title>' + p.date + ": " + p.kg + " kg</title></circle>"; }).join("");
      chart.innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" aria-hidden="true"><line x1="' + P + '" y1="' + (H - P) + '" x2="' + (W - P) + '" y2="' + (H - P) + '" stroke="#29332c"/>' +
        '<path d="' + line + '" fill="none" stroke="#b7ff45" stroke-width="2.5" stroke-linejoin="round"/>' + dots +
        '<text x="' + P + '" y="12" font-size="10" fill="#a3ada5">' + hi.toFixed(1) + ' kg</text><text x="' + P + '" y="' + (H - 6) + '" font-size="10" fill="#a3ada5">' + lo.toFixed(1) + " kg</text></svg>";
    }
  }
})();
