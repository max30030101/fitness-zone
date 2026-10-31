from django.http import Http404
from django.shortcuts import render
from django.urls import reverse

from .content import ARTICLES


def about(request):
    return render(request, "pages/about.html")


def mindset(request):
    return render(request, "pages/mindset_list.html", {"articles": ARTICLES})


def article(request, slug):
    item = next((a for a in ARTICLES if a["slug"] == slug), None)
    if not item:
        raise Http404("Article not found")
    others = [a for a in ARTICLES if a["slug"] != slug][:3]
    name, extra, label = item["link"]
    url = reverse(name, args=[extra]) if name == "pages:article" else reverse(name) + extra
    return render(request, "pages/mindset_detail.html", {"a": item, "others": others, "link_url": url, "link_label": label})
