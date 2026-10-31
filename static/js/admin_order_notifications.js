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
  region.className = "messagelist";
  region.setAttribute("aria-live", "polite");
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
          item.className = "success";
          link.href = notification.url;
          link.textContent = notification.message;
          item.appendChild(link);
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
