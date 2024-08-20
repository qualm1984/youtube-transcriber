import os
import anthropic
import logging
import time
import requests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_with_claude(api_key, transcript_text, max_retries=3, retry_delay=5):
    client = anthropic.Anthropic(api_key=api_key)
    
    full_prompt = f"""Please analyze the following transcript and create a detailed markdown document. 
    Include the following sections:
    1. Summary
    2. Key Points
    3. Detailed Breakdown (with timestamps if available)
    4. Conclusion
    5. Any relevant metadata (speaker names, video title, etc.)

    Transcript:
    {transcript_text}
    """

    for attempt in range(max_retries):
        try:
            logging.info(f"Sending transcript to Claude API for analysis (Attempt {attempt + 1}/{max_retries})...")
            start_time = time.time()
            
            message = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ]
            )
            
            end_time = time.time()
            api_time = end_time - start_time
            logging.info(f"Claude API analysis completed in {api_time:.2f} seconds")
            
            return message.content[0].text

        except anthropic.APIError as e:
            if e.status_code == 400:
                logging.error("Invalid request error: There was an issue with the format or content of your request.")
                raise
            elif e.status_code == 401:
                logging.error("Authentication error: There's an issue with your API key.")
                raise
            elif e.status_code == 403:
                logging.error("Permission error: Your API key does not have permission to use the specified resource.")
                raise
            elif e.status_code == 404:
                logging.error("Not found error: The requested resource was not found.")
                raise
            elif e.status_code == 413:
                logging.error("Request too large: Request exceeds the maximum allowed number of bytes.")
                raise
            elif e.status_code == 429:
                logging.error("Rate limit error: Your account has hit a rate limit.")
                raise
            elif e.status_code == 500:
                logging.error("API error: An unexpected error has occurred internal to Anthropic's systems.")
                raise
            elif e.status_code == 529:
                if attempt < max_retries - 1:
                    logging.warning(f"Overloaded error: Anthropic's API is temporarily overloaded. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    logging.error("Overloaded error: Max retries reached. Anthropic's API is temporarily overloaded.")
                    raise
            else:
                logging.error(f"Unexpected error occurred: {str(e)}")
                raise
        except Exception as e:
            logging.error(f"Unexpected error in Claude API processing: {str(e)}")
            raise

    logging.error("Max retries reached. Failed to process with Claude API.")
    raise Exception("Failed to process with Claude API after multiple attempts.")

# ... [rest of the script remains the same] ...

