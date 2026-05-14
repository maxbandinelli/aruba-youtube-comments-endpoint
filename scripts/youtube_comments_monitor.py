import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3/commentThreads"


def fail(message):
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    sys.exit(1)


def youtube_get(params):
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        fail("Missing YOUTUBE_API_KEY")

    params["key"] = api_key
    url = YOUTUBE_API_BASE + "?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        fail(f"YouTube API error: {exc}")


def normalize_item(item):
    snippet = item.get("snippet", {})
    top = snippet.get("topLevelComment", {}).get("snippet", {})

    video_id = snippet.get("videoId")
    comment_id = item.get("id")

    return {
        "comment_id": comment_id,
        "video_id": video_id,
        "video_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
        "author": top.get("authorDisplayName"),
        "author_channel_url": top.get("authorChannelUrl"),
        "published_at": top.get("publishedAt"),
        "updated_at": top.get("updatedAt"),
        "text": top.get("textDisplay") or top.get("textOriginal"),
        "like_count": top.get("likeCount", 0),
        "total_reply_count": snippet.get("totalReplyCount", 0),
    }


def main():
    channel_id = os.environ.get("YOUTUBE_CHANNEL_ID")
    if not channel_id:
        fail("Missing YOUTUBE_CHANNEL_ID")

    max_results = int(os.environ.get("MAX_RESULTS", "30"))

    params = {
        "part": "snippet",
        "allThreadsRelatedToChannelId": channel_id,
        "order": "time",
        "maxResults": min(max_results, 100),
        "textFormat": "plainText",
    }

    data = youtube_get(params)
    items = [normalize_item(item) for item in data.get("items", [])]

    output = {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "youtube",
        "channel_id": channel_id,
        "count": len(items),
        "items": items,
    }

    os.makedirs("public", exist_ok=True)

    with open("public/youtube-comments-latest.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    with open("public/youtube-comments-digest.md", "w", encoding="utf-8") as f:
        f.write(f"# YouTube comments digest\n\n")
        f.write(f"Generated at: {output['generated_at']}\n\n")
        for item in items:
            f.write(f"## {item.get('author') or 'Unknown author'}\n\n")
            f.write(f"- Video: {item.get('video_url')}\n")
            f.write(f"- Published: {item.get('published_at')}\n")
            f.write(f"- Likes: {item.get('like_count')}\n")
            f.write(f"- Replies: {item.get('total_reply_count')}\n\n")
            f.write(f"{item.get('text') or ''}\n\n")

    print(json.dumps({"ok": True, "count": len(items)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
