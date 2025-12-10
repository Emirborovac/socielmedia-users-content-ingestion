from yt_dlp import YoutubeDL

def get_recent_posts(username, limit=5):
    url = f"https://www.tiktok.com/@{username}"

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,     # Do NOT download videos
        "skip_download": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if "entries" not in info:
        raise Exception("No posts found. User may be private.")

    # take the first N entries
    posts = info["entries"][:limit]

    # extract URLs
    urls = [p["url"] for p in posts]

    return urls


def main():
    username = input("Enter TikTok username (without @): ").strip()
    print(f"\nFetching recent posts from @{username}...\n")

    try:
        urls = get_recent_posts(username)
        print("Recent 5 posts:\n")
        for i, url in enumerate(urls, 1):
            print(f"{i}. {url}")
    except Exception as e:
        print("\nError:", e)


if __name__ == "__main__":
    main()
