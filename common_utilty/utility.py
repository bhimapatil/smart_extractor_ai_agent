import os
import logging
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from AI_Agent.agents_client import BedrockAgent
# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self, folder_paths, prompt_template=str, max_workers=5, callback=None):
        self.folder_paths = folder_paths
        self.prompt_template = prompt_template
        self.max_workers = max_workers
        self.agent = BedrockAgent()
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        self.callback = callback

    def _find_images(self):
        image_paths = []
        for folder_path in self.folder_paths:
            if not os.path.exists(folder_path):
                logger.warning(f"Folder {folder_path} does not exist.")
                continue
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.splitext(file)[1].lower() in self.image_extensions:
                        image_paths.append(file_path)
        return image_paths

    def _process_single_image(self, image_path):
        try:
            prompt = f"{self.prompt_template}"
            response = self.agent.get_response(prompt, image_path)
            return response
        except Exception as e:
            logger.error(f"Error processing {image_path}: {str(e)}")
            return {
                'image_path': image_path,
                'filename': os.path.basename(image_path),
                'ai_response': f"Error: {str(e)}"
            }

    def process_images(self):
        image_paths = self._find_images()
        if not image_paths:
            logger.warning("No images found in the specified folders.")
            return []

        results = []
        total = len(image_paths)
        processed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._process_single_image, img_path): img_path for img_path in image_paths}
            
            for future in as_completed(futures):
                img_path = futures[future]
                try:
                    result = future.result()
                    processed += 1
                    
                    if result:
                        results.append(result)
                        # Notify about successful processing
                        if self.callback:
                            self.callback({
                                "status": "processing",
                                "image": os.path.basename(img_path),
                                "progress": f"{processed}/{total}",
                                "percentage": int((processed/total) * 100),
                                "result": result
                            })
                except Exception as e:
                    logger.error(f"Error processing {img_path}: {str(e)}")
                    # Notify about failed processing
                    if self.callback:
                        self.callback({
                            "status": "error",
                            "image": os.path.basename(img_path),
                            "error": str(e),
                            "progress": f"{processed}/{total}",
                            "percentage": int((processed/total) * 100)
                        })

        return results





