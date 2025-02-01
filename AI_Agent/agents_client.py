# agent.py
import logging
from config import settings
from AI_Agent.agent import BedrockClient

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class BedrockAgent:
    def __init__(self):
        self.client = BedrockClient(
            access_key=settings.bedrock_access_key,
            secret_key=settings.bedrock_secret_access_key
        )
    def get_response(self, prompt, image_path):
        try:
            response = self.client.get_response_from_bedrock(prompt, image_path)
            return response
        except Exception as e:
            logger.error(f"Error getting response for {image_path}: {str(e)}")
            return f"Error: {str(e)}"
