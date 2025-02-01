from typing import Iterator
import boto3
import json
import time
from botocore.config import Config
import os
import sys
import base64
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import settings

class BedrockClient:
    def __init__(self, access_key, secret_key, region="ap-south-1"):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.bedrock_client = self.initialize_bedrock_client()

    def initialize_bedrock_client(self):
        config = Config(retries={"max_attempts": 10})
        return boto3.client(
            service_name='bedrock-runtime',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=config
        )

    def get_response_from_bedrock(self, prompt, image_path=None):
        messages = [
            {
                "role": "user",
                "content": []
            }
        ]
        if image_path:
            with open(image_path, "rb") as image_file:
                image_bytes = image_file.read()
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            messages[0]["content"].append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_base64
                }
            })

        if prompt:
            messages[0]["content"].append({
                "type": "text",
                "text": prompt
            })

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": messages
        }
        inference_profile_arn = "arn:aws:bedrock:ap-south-1:725794772865:inference-profile/apac.anthropic.claude-3-5-sonnet-20240620-v1:0"
        try:
            response = self.bedrock_client.invoke_model(
                modelId=inference_profile_arn,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )
            response_body = json.loads(response['body'].read().decode("utf-8"))
            print("Response Body:", response_body)
            if 'content' in response_body:
                return response_body['content'][0]['text']
            else:
                print("Error: 'content' key not found in the response.")
                return ""
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            time.sleep(1)
            return ""

    def get_response_streaming_from_bedrock(self, prompt, image_path=None) -> Iterator[str]:
        messages = [
            {
                "role": "user",
                "content": []
            }
        ]

        if image_path:
            pass

        if prompt:
            messages[0]["content"].append({
                "type": "text",
                "text": prompt
            })

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": messages
        }

        inference_profile_arn = "arn:aws:bedrock:ap-south-1:725794772865:inference-profile/apac.anthropic.claude-3-5-sonnet-20240620-v1:0"

        try:
            response = self.bedrock_client.invoke_model_with_response_stream(
                modelId=inference_profile_arn,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            for event in response['body']:
                try:
                    chunk = json.loads(event['chunk']['bytes'])
                    # Handle different response structures
                    if isinstance(chunk, dict):
                        if 'content' in chunk and isinstance(chunk['content'], list):
                            for content_item in chunk['content']:
                                if content_item.get('type') == 'text':
                                    yield content_item.get('text', '')
                        elif 'delta' in chunk and 'text' in chunk['delta']:
                            yield chunk['delta']['text']
                except Exception as e:
                    print(f"Error processing chunk: {str(e)}")
                    continue

        except Exception as e:
            print(f"Error in streaming response: {str(e)}")
            yield ""

# def check_bedrock_connection():
#     ACCESS_KEY = settings.bedrock_access_key
#     SECRET_KEY = settings.bedrock_secret_access_key
#     REGION = "ap-south-1"
#
#     client = BedrockClient(access_key=ACCESS_KEY, secret_key=SECRET_KEY, region=REGION)
#     path_to_img = r"C:\Users\bhimashankar.r.REWARD360\Desktop\git_clones\generic_ai_agent\sample_invoce.jpeg"
#     print(path_to_img)
#     test_prompt = "extract text from image"
#
#     try:
#         response = client.get_response_from_bedrock(test_prompt,path_to_img)
#         if response:
#             return "Bedrock Connection successful"
#         else:
#             return "No response received or an error occurred."
#     except (NoCredentialsError, PartialCredentialsError):
#         return "Credentials not found or incomplete."
#     except Exception as e:
#         return f"Connection test failed: {str(e)}"
#
# # Example usage:
# if __name__ == "__main__":
#     connection_status = check_bedrock_connection()
#     print(connection_status)
#
#
