"""Curated sample asset URLs for media/3D modalities.

These are used as a fallback when Tavily cannot provide enough direct
asset URLs for a given request, so that the POC always has some
multi-modal data to export.
"""

from typing import Dict, List, TypedDict


class SampleAsset(TypedDict, total=False):
    url: str
    title: str
    description: str


SAMPLE_ASSETS: Dict[str, List[SampleAsset]] = {
    "audio": [
        {
            "url": "https://file-examples.com/wp-content/uploads/2017/11/file_example_MP3_700KB.mp3",
            "title": "Sample MP3 audio",
            "description": "Short sample MP3 clip from file-examples.com",
        },
        {
            "url": "https://file-examples.com/wp-content/uploads/2017/11/file_example_WAV_1MG.wav",
            "title": "Sample WAV audio",
            "description": "Short sample WAV clip from file-examples.com",
        },
    ],
    "video": [
        {
            "url": "https://file-examples.com/wp-content/uploads/2018/04/file_example_MP4_480_1_5MG.mp4",
            "title": "Sample MP4 video (480p)",
            "description": "Small MP4 sample suitable for quick tests",
        },
        {
            "url": "https://sample-videos.com/video321/mp4/480/big_buck_bunny_480p_1mb.mp4",
            "title": "Big Buck Bunny sample (480p)",
            "description": "Public domain sample clip of Big Buck Bunny",
        },
    ],
    "3d": [
        {
            "url": "https://people.sc.fsu.edu/~jburkardt/data/obj/bunny.obj",
            "title": "Stanford Bunny OBJ",
            "description": "Classic Stanford bunny mesh in OBJ format",
        },
        {
            "url": "https://graphics.stanford.edu/pub/3Dscanrep/bunny/reconstruction/bun_zipper.ply",
            "title": "Stanford Bunny PLY",
            "description": "Stanford bunny mesh in PLY format",
        },
    ],
}
