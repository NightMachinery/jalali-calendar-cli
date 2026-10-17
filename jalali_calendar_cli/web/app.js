// Holiday calendar page. Every month is already rendered by the generator; this only
// chooses which ones to show, marks today, shows each day's tooltip, and remembers the
// view, the theme and the checkboxes.
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
  // In page order, from the months themselves: a page with one view has no view buttons.
  var views = [];
  sections.forEach(function (s) {
    if (views.indexOf(s.dataset.view) < 0) views.push(s.dataset.view);
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

  // A checkbox remembered under `key`; on unless it was turned off, or off unless it was
  // turned on, depending on `byDefault`.
  function option(id, key, byDefault, onChange) {
    var box = document.getElementById(id);
    var saved = load(key);
    box.checked = saved === null ? byDefault : saved === "1";
    box.addEventListener("change", function () {
      store(key, box.checked ? "1" : "0");
      onChange();
    });
    return box;
  }

  // The number of columns the year grid has at the current width.
  function gridColumns() {
    return getComputedStyle(main).gridTemplateColumns.split(" ").length;
  }

  function render() {
    hideTip();
    var list = byView[state.view];
    var index = find(state.view, state.anchor);
    var current = list[index];
    sections.forEach(function (s) {
      s.hidden = true;
    });
    main.className = state.mode;
    if (state.mode === "month") {
      current.hidden = false;
      // the next month, so that the turn of the month can be planned across
      if (showNextMonth.checked && list[index + 1]) list[index + 1].hidden = false;
    } else {
      var last = -1;
      list.forEach(function (s, i) {
        if (s.dataset.year === current.dataset.year) {
          s.hidden = false;
          last = i;
        }
      });
      // the first row of the next year, so that the turn of the year can be planned across
      if (showNextRow.checked) {
        var extra = gridColumns();
        for (var j = last + 1; j <= last + extra && j < list.length; j++) list[j].hidden = false;
      }
    }
    optionLabels.forEach(function (l) {
      l.hidden = l.dataset.mode !== state.mode;
    });
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
  function applyNotes() {
    main.classList.toggle("hide-notes", !showNotes.checked);
  }
  var showNotes = option("show-notes", "cal-notes", false, applyNotes);
  var showNextMonth = option("show-next-month", "cal-next-month", true, render);
  var showNextRow = option("show-next-row", "cal-next-row", true, render);
  var optionLabels = Array.prototype.slice.call(document.querySelectorAll(".option[data-mode]"));

  // The year grid's column count, and so the next row, depends on the width.
  var lastColumns = 0;
  window.addEventListener("resize", function () {
    if (state.mode !== "year") return;
    var columns = gridColumns();
    if (columns !== lastColumns) {
      lastColumns = columns;
      render();
    }
  });

  // The color key and the checkboxes, collapsed unless opened; remembered.
  var keyBox = document.getElementById("key");
  var keyButton = document.getElementById("key-toggle");
  function applyKey(open) {
    keyBox.hidden = !open;
    keyButton.setAttribute("aria-expanded", String(open));
  }
  applyKey(load("cal-key") === "1");
  keyButton.addEventListener("click", function () {
    var open = keyBox.hidden;
    applyKey(open);
    store("cal-key", open ? "1" : "0");
  });

  // The browser's bar (the title bar of the installed app) in the page's background color.
  var themeColor = document.querySelector('meta[name="theme-color"]');
  function applyThemeColor() {
    themeColor.content = getComputedStyle(document.documentElement).getPropertyValue("--bg").trim();
  }
  applyThemeColor();
  document.getElementById("theme").addEventListener("click", function () {
    var root = document.documentElement;
    var next = root.dataset.theme === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    store("cal-theme", next);
    applyThemeColor();
  });
  document.addEventListener("keydown", function (e) {
    if (e.target.closest && e.target.closest("input, textarea")) return;
    if (e.key === "ArrowLeft") step(-1);
    if (e.key === "ArrowRight") step(1);
  });

  // --- Tooltips -------------------------------------------------------------------
  // Each day shows its date in both calendars and, from its `data-tip`, its holidays. One
  // element, positioned by hand rather than the browser's native title tooltip: it opens on
  // hover with a mouse, on tap with a finger or pen (tap again or elsewhere to close), and
  // on keyboard focus.

  function el(tag, className, text) {
    var e = document.createElement(tag);
    if (className) e.className = className;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  // The other calendar's date of `day`, from the section's `data-other`: where each of
  // its months starts in this grid (written by the generator; nothing is converted here).
  function otherDate(section, day) {
    if (!section._other) section._other = JSON.parse(section.dataset.other);
    var segment = section._other[0];
    section._other.forEach(function (s) {
      if (s[0] <= day) segment = s;
    });
    return segment[1] + day - segment[0] + " " + segment[2] + " " + segment[3];
  }

  function fillTip(td) {
    var section = td.closest("section.month");
    var day = +td.textContent;
    var weekday = section.querySelectorAll("thead th")[td.cellIndex].textContent;
    tip.textContent = "";
    var head = el("div", "tip-date", weekday + " " + day + " " + section.dataset.label);
    head.appendChild(el("span", "tip-other", otherDate(section, day)));
    tip.appendChild(head);
    if (!td.dataset.tip) return;
    var data = JSON.parse(td.dataset.tip);
    if (data.h.length) {
      var list = el("ul");
      data.h.forEach(function (h) {
        var item = el("li", h[2] ? "secondary" : "primary");
        if (h[0]) item.appendChild(el("span", "tag", h[0]));
        item.appendChild(el("span", "name", h[1]));
        list.appendChild(item);
      });
      tip.appendChild(list);
    }
    if (data.b) tip.appendChild(el("div", "tip-both", "both free"));
  }

  // Above the day, or below it when there is no room above; kept inside the viewport, with
  // the arrow still pointing at the day.
  function placeTip(td) {
    var margin = 8;
    var gap = 8;
    var cell = td.getBoundingClientRect();
    tip.classList.remove("below");
    var width = tip.offsetWidth;
    var height = tip.offsetHeight;
    var top = cell.top - height - gap;
    if (top < margin) {
      top = cell.bottom + gap;
      tip.classList.add("below");
    }
    var center = cell.left + cell.width / 2;
    var left = Math.max(margin, Math.min(window.innerWidth - width - margin, center - width / 2));
    tip.style.top = top + "px";
    tip.style.left = left + "px";
    tip.style.setProperty("--arrow-x", Math.max(12, Math.min(width - 12, center - left)) + "px");
  }

  var tip = el("div", "tip");
  tip.id = "tip";
  tip.setAttribute("role", "tooltip");
  tip.hidden = true;
  document.body.appendChild(tip);
  var tipCell = null;

  function showTip(td) {
    if (tipCell === td && !tip.hidden) return;
    hideTip();
    tipCell = td;
    fillTip(td);
    tip.hidden = false;
    placeTip(td);
    td.setAttribute("aria-describedby", "tip");
  }

  function hideTip() {
    if (tipCell) tipCell.removeAttribute("aria-describedby");
    tipCell = null;
    tip.hidden = true;
  }

  // The day cell an event happened in, if any (empty cells have no day).
  function dayCell(target) {
    var td = target.closest ? target.closest("tbody td") : null;
    return td && td.textContent ? td : null;
  }

  // Every day can be reached with the keyboard.
  Array.prototype.forEach.call(document.querySelectorAll("tbody td"), function (td) {
    if (td.textContent) td.tabIndex = 0;
  });

  var lastPointer = "mouse";
  document.addEventListener("pointerdown", function (e) {
    lastPointer = e.pointerType;
  });
  main.addEventListener("pointerover", function (e) {
    var td = e.pointerType === "mouse" && dayCell(e.target);
    if (td) showTip(td);
  });
  main.addEventListener("pointerout", function (e) {
    var td = e.pointerType === "mouse" && dayCell(e.target);
    if (td && td === tipCell && !td.contains(e.relatedTarget)) hideTip();
  });
  document.addEventListener("click", function (e) {
    var td = dayCell(e.target);
    if (!td) return hideTip();
    if (lastPointer === "mouse") return;
    if (td === tipCell && !tip.hidden) hideTip();
    else showTip(td);
  });
  // Focus from a tap is not `:focus-visible`, so only keyboard focus opens it here.
  main.addEventListener("focusin", function (e) {
    var td = dayCell(e.target);
    if (td && td.matches(":focus-visible")) showTip(td);
  });
  main.addEventListener("focusout", function (e) {
    if (dayCell(e.target) === tipCell && lastPointer === "mouse") hideTip();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") hideTip();
  });
  window.addEventListener("scroll", hideTip, { passive: true });
  window.addEventListener("resize", hideTip);

  render();

  // Offline copies, for the installed app (sw.js). Not available on file:// or plain HTTP.
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(function () {});
})();
