(function () {
  "use strict";

  var script = document.currentScript;
  var content = document.getElementById("content");
  if (!script || !content || !script.dataset.endpoint || !script.dataset.since) return;

  var list = document.createElement("ul");
  var region = document.createElement("div");
  var seen = new Set();
  var since = script.dataset.since;
  var lastCheckedAt = null;
  var polling = false;
  region.className = "admin-order-alerts";
  region.setAttribute("role", "region");
  region.setAttribute("aria-label", "New shop alerts");
  region.setAttribute("aria-live", "assertive");
  region.setAttribute("aria-relevant", "additions");
  region.hidden = true;
  region.appendChild(list);
  content.insertBefore(region, content.firstChild);

  function poll() {
    if (polling) return;
    polling = true;
    var url = new URL(script.dataset.endpoint, window.location.href);
    var querySince = lastCheckedAt
      ? new Date(Date.parse(lastCheckedAt) - 60000).toISOString()
      : since;
    url.searchParams.set("since", querySince);

    fetch(url.toString(), { credentials: "same-origin", headers: { "Accept": "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("Order notification request failed: " + response.status);
        return response.json();
      })
      .then(function (data) {
        (data.notifications || []).forEach(function (notification) {
          var id = String(notification.id);
          if (seen.has(id)) return;
          seen.add(id);

          var item = document.createElement("li");
          var link = document.createElement("a");
          var close = document.createElement("button");
          item.className = "admin-order-alert admin-order-alert--" + notification.event_type;
          link.href = notification.url;
          link.textContent = notification.message;
          close.type = "button";
          close.className = "admin-order-alert__close";
          close.setAttribute("aria-label", "Dismiss notification");
          close.textContent = "\u00d7";
          close.addEventListener("click", function () {
            item.remove();
            if (!list.children.length) region.hidden = true;
          });
          item.appendChild(link);
          item.appendChild(close);
          list.appendChild(item);
          region.hidden = false;
        });
        lastCheckedAt = data.checked_at || lastCheckedAt;
      })
      .catch(function (error) {
        console.error(error);
      })
      .then(function () {
        polling = false;
      });
  }

  poll();
  window.setInterval(poll, 30000);
})();
