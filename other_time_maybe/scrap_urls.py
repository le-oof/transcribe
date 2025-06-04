import requests
import re
from bs4 import BeautifulSoup
from typing import List, Tuple

class ScrapUrlError(Exception):
    pass

def scrap_video_urls(
    local_html_path: str = 'page.html',
    instancename_regex: str = 'Видео',
    max_instances: int = 100
) -> List[str]:
    """
    Parse a local HTML file for links whose <span class="instancename"> text matches instancename_regex.
    For each such link, fetch the linked page and find unique .mp4 video URLs.
    Returns a list of these video URLs, sorted by the name (title) of the page they are on.
    Raises ScrapUrlError if the number of unique video URLs exceeds max_instances.
    """
    # Parse the local HTML file
    try:
        with open(local_html_path, encoding='utf-8') as f:
            html = f.read()
    except Exception as e:
        raise ScrapUrlError(f"Failed to read local HTML file: {e}")

    soup = BeautifulSoup(html, 'html.parser')
    # Find all links whose instancename matches the regex
    all_links = set()
    for a in soup.find_all('a', href=True):
        instancename_span = a.find('span', class_='instancename')
        if instancename_span:
            text = instancename_span.get_text(separator=' ', strip=True)
            # print(f'instancename text: "{text}"')
            if re.search(instancename_regex, text, re.IGNORECASE):
                href = a['href']
                # Assume all child links are absolute URLs
                all_links.add(href)

    # print('Found child links:', all_links)

    video_url_to_title: dict = {}
    for link in all_links:
        try:
            page_resp = requests.get(link)
            page_resp.raise_for_status()
        except Exception as e:
            continue  # skip broken links
        page_soup = BeautifulSoup(page_resp.text, 'html.parser')
        print(page_resp.text)
        break
        page_title = page_soup.title.string.strip() if page_soup.title else link
        # Find all .mp4 links
        found = set()
        # Search for <video> tags
        for video in page_soup.find_all('video'):
            src = video.get('src')
            if src and src.endswith('.mp4'):
                found.add(requests.compat.urljoin(link, src))
            # Also check <source> tags inside <video>
            for source in video.find_all('source'):
                s = source.get('src')
                if s and s.endswith('.mp4'):
                    found.add(requests.compat.urljoin(link, s))
        # Search for direct links to .mp4 in <a> tags
        for a in page_soup.find_all('a', href=True):
            href = a['href']
            if href.endswith('.mp4'):
                found.add(requests.compat.urljoin(link, href))
        # Search for .mp4 URLs in the raw HTML (in case they're embedded in JS)
        for match in re.findall(r'("|\')((?:https?:)?//[^\"\']+\.mp4)("|\')', page_resp.text):
            url = match[1]
            if not url.startswith('http'):
                url = requests.compat.urljoin(link, url)
            found.add(url)
        for vurl in found:
            video_url_to_title[vurl] = page_title

    unique_video_urls = list(video_url_to_title.keys())
    if len(unique_video_urls) > max_instances:
        raise ScrapUrlError(f"Found {len(unique_video_urls)} video URLs, which exceeds the maximum allowed: {max_instances}")
    # Sort by page title
    sorted_urls = sorted(unique_video_urls, key=lambda u: video_url_to_title[u])
    return sorted_urls

if __name__ == "__main__":
    # Example usage
    # url = input("Enter the global URL: ")
    # regex = input("Enter the link regex: ")
    # max_count = int(input("Enter the max number of video instances: "))
    try:
        videos = scrap_video_urls()
        print(f"Found {len(videos)} video URLs:")
        for v in videos:
            print(v)
    except ScrapUrlError as e:
        print(f"Error: {e}")
