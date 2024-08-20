import os
import anthropic
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def read_transcript(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error reading transcript file: {str(e)}")
        raise

def process_with_claude(api_key, transcript_text):
    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        logging.info("Sending transcript to Claude API for analysis...")
        start_time = time.time()
        
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
    except Exception as e:
        logging.error(f"Error in Claude API processing: {str(e)}")
        raise

def write_markdown(file_path, content):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logging.info(f"Markdown content written to file: {file_path}")
    except Exception as e:
        logging.error(f"Error writing markdown file: {str(e)}")
        raise

def main():
    # Replace these with your actual file paths and API key
    transcript_file = "Hang In There Kathy.txt"
    output_file = "Hang In There Kathy_analysis.md"
    api_key = "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"

    try:
        # Read the transcript
        transcript_text = read_transcript(transcript_file)
        logging.info("Transcript read successfully")

        # Process with Claude API
        markdown_output = process_with_claude(api_key, transcript_text)

        # Write the markdown output
        write_markdown(output_file, markdown_output)

        logging.info("Process completed successfully")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
