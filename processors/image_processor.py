from pathlib import Path
from PIL import Image

class ImageProcessor:
    @staticmethod
    def is_image_file(filename: str) -> bool:
        return any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif'])
    
    @staticmethod
    async def load_image(image_path: Path) -> Image.Image:
        return Image.open(image_path)
