import anthropic
import time
import logging

def process_with_claude(api_key, transcript_text, max_retries=3, retry_delay=5):
    client = anthropic.Anthropic(api_key=api_key)
    full_prompt = f"""Please analyze the following transcript and create a detailed markdown document.
    Include the following sections:
    Summary
    Key Points
    Detailed Breakdown (with timestamps if available)
    Conclusion
    Any relevant metadata (speaker names, video title, etc.)
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
            if e.status_code == 529:
                if attempt < max_retries - 1:
                    logging.warning(f"Overloaded error: Anthropic's API is temporarily overloaded. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    logging.error("Overloaded error: Max retries reached. Anthropic's API is temporarily overloaded.")
                    raise
            else:
                logging.error(f"API error: {str(e)}")
                raise
        except Exception as e:
            logging.error(f"Unexpected error in Claude API processing: {str(e)}")
            raise
    logging.error("Max retries reached. Failed to process with Claude API.")
    raise Exception("Failed to process with Claude API after multiple attempts.")

def read_transcript(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error reading transcript file: {str(e)}")
        raise