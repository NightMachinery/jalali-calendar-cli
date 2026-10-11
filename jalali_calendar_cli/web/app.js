// Holiday calendar page. Every month is already rendered by the generator; this only
// chooses which ones to show, marks today, and remembers the view, the theme and whether
// the holiday lists are shown.
(function () {
  "use strict";

  var main = document.getElementById("months");
  var sections = Array.prototype.slice.call(document.querySelectorAll("section.month"));
  var legends = Array.prototype.slice.call(document.querySelectorAll(".legend"));
  var viewButtons = Array.prototype.slice.call(document.querySelectorAll("[data-set-view]"));
  var modeButtons = Array.prototype.slice.call(document.querySelectorAll("[data-set-mode]"));

  var byView = {};
  sections.forEach(function (s) {
    (byView[s.dataset.view] = byView[s.dataset.view] || []).push(s);
  });
  var views = viewButtons.map(function (b) {
    return b.dataset.setView;
  });

  function pad(n) {
    return (n < 10 ? "0" : "") + n;
  }

  function isoLocal(d) {
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }

  function dayIndex(iso) {
    var p = iso.split("-");
    return Date.UTC(+p[0], +p[1] - 1, +p[2]) / 86400000;
  }

  var today = isoLocal(new Date());

  // Mark today in every view.
  sections.forEach(function (s) {
    if (s.dataset.start <= today && today <= s.dataset.end) {
      var day = String(dayIndex(today) - dayIndex(s.dataset.start) + 1);
      Array.prototype.forEach.call(s.querySelectorAll("tbody td"), function (td) {
        if (td.textContent === day) td.classList.add("today");
      });
    }
  });

  function store(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (e) {}
  }

  function load(key) {
    try {
      return localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  // The index of the month of `view` that contains `date`, or the nearest one.
  function find(view, date) {
    var list = byView[view];
    for (var i = 0; i < list.length; i++) {
      if (list[i].dataset.start <= date && date <= list[i].dataset.end) return i;
    }
    return date < list[0].dataset.start ? 0 : list.length - 1;
  }

  var state = {
    view: views[0],
    mode: "month",
    anchor: today,
  };

  var hash = location.hash.replace(/^#/, "").split("/");
  var savedView = hash[0] || load("cal-view");
  var savedMode = hash[1] || load("cal-mode");
  if (views.indexOf(savedView) >= 0) state.view = savedView;
  if (savedMode === "month" || savedMode === "year") state.mode = savedMode;
  if (/^\d{4}-\d{2}-\d{2}$/.test(hash[2] || "")) state.anchor = hash[2];

  function render() {
    var list = byView[state.view];
    var current = list[find(state.view, state.anchor)];
    sections.forEach(function (s) {
      s.hidden = true;
    });
    if (state.mode === "month") {
      current.hidden = false;
    } else {
      list.forEach(function (s) {
        if (s.dataset.year === current.dataset.year) s.hidden = false;
      });
    }
    main.className = state.mode;
    applyNotes();
    legends.forEach(function (l) {
      l.hidden = l.dataset.view !== state.view;
    });
    viewButtons.forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.setView === state.view));
    });
    modeButtons.forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.setMode === state.mode));
    });
    history.replaceState(null, "", "#" + [state.view, state.mode, state.anchor].join("/"));
    store("cal-view", state.view);
    store("cal-mode", state.mode);
  }

  function step(delta) {
    var list = byView[state.view];
    var i = find(state.view, state.anchor);
    if (state.mode === "month") {
      i = Math.max(0, Math.min(list.length - 1, i + delta));
      state.anchor = list[i].dataset.start;
    } else {
      var year = String(+list[i].dataset.year + delta);
      for (var j = 0; j < list.length; j++) {
        if (list[j].dataset.year === year) {
          state.anchor = list[j].dataset.start;
          break;
        }
      }
    }
    render();
  }

  viewButtons.forEach(function (b) {
    b.addEventListener("click", function () {
      state.view = b.dataset.setView;
      render();
    });
  });
  modeButtons.forEach(function (b) {
    b.addEventListener("click", function () {
      state.mode = b.dataset.setMode;
      render();
    });
  });
  document.getElementById("prev").addEventListener("click", function () {
    step(-1);
  });
  document.getElementById("next").addEventListener("click", function () {
    step(1);
  });
  document.getElementById("today").addEventListener("click", function () {
    state.anchor = today;
    render();
  });
  // The holiday lists under the months are hidden unless asked for.
  var showNotes = document.getElementById("show-notes");
  function applyNotes() {
    main.classList.toggle("hide-notes", !showNotes.checked);
  }
  showNotes.checked = load("cal-notes") === "1";
  showNotes.addEventListener("change", function () {
    store("cal-notes", showNotes.checked ? "1" : "0");
    applyNotes();
  });

  document.getElementById("theme").addEventListener("click", function () {
    var root = document.documentElement;
    var next = root.dataset.theme === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    store("cal-theme", next);
  });
  document.addEventListener("keydown", function (e) {
    if (e.target.closest && e.target.closest("input, textarea")) return;
    if (e.key === "ArrowLeft") step(-1);
    if (e.key === "ArrowRight") step(1);
  });

  render();
})();
