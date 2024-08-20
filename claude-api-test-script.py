import anthropic
import os

def test_claude_api(api_key):
    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        print("Sending request to Claude API...")
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": "Please write a short paragraph about the importance of API testing."
                }
            ]
        )
        print("Received response from Claude API:")
        print(message.content[0].text)
        return True
    except Exception as e:
        print(f"Error calling Claude API: {str(e)}")
        return False

if __name__ == "__main__":
    api_key = input("Please enter your Claude API key: ")
    success = test_claude_api(api_key)
    if success:
        print("Claude API test successful!")
    else:
        print("Claude API test failed. Please check your API key and internet connection.")
