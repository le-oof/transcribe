from typing import List

def generate_video_urls(
    course_codes: List[str] = ['HIS-00', 'HIS-10'],
    section_range: range = range(1, 11),
    part_range: range = range(1, 10),
    base_url: str = "https://mooc.tsu.ru/mooc/"
) -> List[str]:
    """
    Generate video URLs for multiple courses, with or without 's' prefix in filenames.
    Args:
        course_codes: list of course codes, e.g., ['HIS-10', 'HIS-11']
        section_range: range of section numbers (e.g., range(1, 11))
        part_range: range of part numbers (e.g., range(1, 5))
        use_s_prefix: if True, filenames are s.<section>.<part>.mp4, else <section>.<part>.mp4
        base_url: the base URL (default: https://mooc.tsu.ru/mooc/)
    Returns:
        List of full URLs as strings.
    """
    urls = []
    for code in course_codes:
        for section in section_range:
            for part in part_range:
                for use_s_prefix in [True, False]:
                    filename = f"s.{section}.{part}.mp4" if use_s_prefix else f"{section}.{part}.mp4"
                    url = f"{base_url}{code}/{filename}"
                    urls.append(url)
    return urls
