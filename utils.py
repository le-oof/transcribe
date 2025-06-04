from typing import List
import requests
from tqdm import tqdm

def generate_video_urls(
    section_range: range = range(1, 6),
    part_range: range = range(1, 7),
    base_url: str = "https://mooc.tsu.ru/mooc/"
) -> List[str]:
    """
    Generate video URLs for multiple courses, with or without 's' prefix in filenames.
    Args:
        section_range: range of section numbers (e.g., range(1, 11))
        part_range: range of part numbers (e.g., range(1, 5))
        base_url: the base URL (default: https://mooc.tsu.ru/mooc/)
    Returns:
        List of full URLs as strings.
    """
    urls = []
    for use_s_prefix, code in zip([False, True], ['HIS-00', 'HIS-10']) :
        for section in tqdm(section_range):
            for part in part_range:
                filename = f"s.{section}.{part}.mp4" if use_s_prefix else f"{section}.{part}.mp4"
                url = f"{base_url}{code}/{filename}"
                try:
                    resp = requests.head(url, timeout=10)
                    if resp.status_code == 200:
                        urls.append(url)
                except requests.RequestException:
                    continue
    return sorted(urls)


def sanitize_filename(name):
    return ''.join(c for c in name if c.isalnum() or c in (' ', '.', '.', '_', '-')).rstrip()