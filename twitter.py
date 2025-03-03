import os
import requests
import openai
import time
from dotenv import load_dotenv

load_dotenv()
# Load your OpenAI API key from an environment variable
openai.api_key = os.getenv("OPENAI_AI_KEY")
bearer_token = os.getenv("BEARER_TOKEN")

# Check for API keys
if not openai.api_key:
    print("API key not found. Please set the 'OPENAI_API_KEY' environment variable.")
    exit(1)

if not bearer_token:
    print("Bearer token not found. Please set the 'BEARER_TOKEN' environment variable.")
    exit(1)

# Define the Twitter API endpoint and query parameters
url = "https://api.twitter.com/2/tweets/search/recent"
topics = ["tariffs", "russia"] 
current_topic_index = 0  
delay = 15 * 60 

headers = {"Authorization": f"Bearer {bearer_token}"}

while True:
    topic = topics[current_topic_index]
    print(f"Gathering tweets about: {topic}")

    params = {
        "query": topic,
        "max_results": 5 
    }

    try:
        # Fetch tweets
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()

            if data.get("meta", {}).get("result_count", 0) == 0:
                print(f"No tweets found for the topic: {topic}")
                tweets_text = f"No recent tweets found for the topic: {topic}."
            else:
                tweets = [tweet["text"] for tweet in data.get("data", [])]
                tweets_text = "\n".join(tweets)

            # Pass tweets to OpenAI
            print("Generating summary and news script...")
            try:
                ai_response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {
                            "role": "user",
                            "content": f"Summarize these tweets and write a news script:\n\n{tweets_text}"
                        }
                    ],
                    max_tokens=300
                )
                news_script = ai_response['choices'][0]['message']['content']
                print(f"Generated News Script:\n{news_script}")

                # Save to file
                with open("news.txt", "a") as file:
                    file.write(f"\n--- News Script for Topic: {topic} ---\n")
                    file.write(news_script)
                    file.write("\n")
                print("News script saved to news.txt")

            except openai.error.OpenAIError as e:
                print(f"Error generating response from OpenAI: {e}")

        else:
            print(f"Error fetching tweets: {response.status_code} - {response.text}")

    except requests.RequestException as e:
        print(f"Error with Twitter API request: {e}")

    # Move to the next topic
    current_topic_index = (current_topic_index + 1) % len(topics)

    # Wait for 15 minutes
    print("Waiting for 15 minutes before fetching the next topic...")
    time.sleep(delay)


