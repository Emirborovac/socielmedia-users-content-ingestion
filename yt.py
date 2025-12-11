from yt_dlp import YoutubeDL

def normalize_url(channel_input: str, content_type: str) -> str:
    """
    content_type = 'videos' or 'shorts'
    """
    channel_input = channel_input.strip()

    # Already a full URL
    if channel_input.startswith("http"):
        if f"/{content_type}" not in channel_input:
            return channel_input.rstrip("/") + f"/{content_type}"
        return channel_input

    # @handle
    if channel_input.startswith("@"):
        return f"https://www.youtube.com/{channel_input}/{content_type}"

    # Channel ID (UCxxxx)
    if channel_input.startswith("UC"):
        return f"https://www.youtube.com/channel/{channel_input}/{content_type}"

    # Custom channel name
    return f"https://www.youtube.com/c/{channel_input}/{content_type}"


def get_recent_posts(channel_input: str, content_type: str, limit: int = 5):
    """
    content_type = 'videos' or 'shorts'
    """

    url = normalize_url(channel_input, content_type)

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,  # we only want metadata
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = info.get("entries") or []
    if not entries:
        raise Exception(f"No {content_type} found for this channel.")

    # Take first 5 entries as-is (YouTube sorts newest → oldest)
    recent = entries[:limit]

    result_urls = []
    for e in recent:
        if "url" in e and e["url"]:
            result_urls.append(e["url"])
        else:
            result_urls.append(f"https://www.youtube.com/watch?v={e['id']}")

    return result_urls


def main():
    channel = input("Enter YouTube @handle, channel URL, or channel ID: ").strip()

    print("\nChoose content type:")
    print("1 = Recent 5 normal videos")
    print("2 = Recent 5 shorts")

    choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        content_type = "videos"
    elif choice == "2":
        content_type = "shorts"
    else:
        print("Invalid option.")
        return

    print(f"\nFetching recent 5 {content_type} from: {channel}\n")

    try:
        urls = get_recent_posts(channel, content_type)
        for i, url in enumerate(urls, 1):
            print(f"{i}. {url}")
    except Exception as e:
        print("\nError:", e)


if __name__ == "__main__":
    main()
