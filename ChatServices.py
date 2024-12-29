import uuid
from openai import OpenAI
import datetime
import time
import os
from helper import Helper
from dotenv import load_dotenv
import random

load_dotenv()

class Model:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.chat_sessions = {}  # Maps phone numbers to session tokens
        self.system_prompt = {"role": "system", "content": (
            "You are a chatbot for Ashton Company. "
            "You are an AI assistant designed to help users with any questions or tasks they have. "
            "You should respond in a friendly, professional, and concise manner. "
            "Be proactive in asking clarifying questions if the user's query is unclear, and provide examples when necessary. "
            "If the user asks for technical explanations, provide them in simple terms, avoiding jargon. "
            "You can handle casual conversations and provide suggestions, but always remain respectful and helpful. "
            "If you do not know the answer, admit it honestly and guide the user on how they might find the information. "
            "Your goal is to create a positive, engaging, and informative interaction."
        )}

    def generate_token(self):
        """Generate a unique session token."""
        return str(uuid.uuid4())

    def initialize_chat_history(self, token):
        """Initialize chat history for a specific session."""
        self.chat_sessions[token] = [self.system_prompt]

    def get_response(self, user_input, token):
        """Generate a response to the user's input for a specific session."""
        if token not in self.chat_sessions:
            raise ValueError("Invalid session token. Please initialize a new session.")

        # Add user input to the session's chat history
        self.chat_sessions[token].append({"role": "user", "content": user_input})

        # Generate response
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=self.chat_sessions[token],
        )

        # Extract the response text from the returned object
        response_str = response['choices'][0]['message']['content']

        # Add the AI's response to the session's chat history
        self.chat_sessions[token].append({"role": "assistant", "content": response_str})

        return response_str



    def image_description(self, image_path, token):
        """
        Generate and yield descriptions one by one for a specific session.

        :param image_path: Path to the image.
        :param token: Session token to track chat history.
        :return: A generator yielding complements.
        """
        if token not in self.chat_sessions:
            raise ValueError("Invalid session token. Please initialize a new session.")

        PROMPT_BASE = (
            "Your task is to complement the person in the image based on their outfit or something relevant to them. "
            "Don't assume anything; give a response according to the image provided. "
            "Avoid words like 'I can't see the image'."
        )

        # Encode the image to base64
        base64_image = Helper.encode_image(image_path)

        # List of topics to focus on
        Things_to_talk_about = ["outfit", "shoes", "attitude in the environment"]
        
        for topic in Things_to_talk_about:
            # Add slight variations to the prompt for diversity
            variation_prompt = (
                PROMPT_BASE + f" You can talk about the person's {topic}. Change your tone a bit while being friendly, inviting, and respectful."
            )

            history = self.chat_sessions[token] + [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Given the following base64-encoded image + {variation_prompt}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ],
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.9,  # Slightly higher temperature for more diverse outputs
                max_tokens=500,
                messages=history,
                stream=True,
            )

            # Stream and collect the AI's response
            response_str = ""
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    response_str += chunk.choices[0].delta.content

            # Update chat history
            self.chat_sessions[token].append({"role": "assistant", "content": response_str.strip()})

            # Yield the generated complement
            yield response_str.strip()


# Main interactive loop
if __name__ == "__main__":
    model = Model()

    print("Welcome to Ashton Chatbot. Type 'exit' to end the chat.")
    session_token = model.generate_token()
    model.initialize_chat_history(session_token)
    print(f"Your session token: {session_token}")
    
    flag = False
    while True:
        if flag == False:
            model.image_description('hi_gesture.jpg', session_token)
            flag = True
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        elif user_input.startswith("image:"):
            # Handle image input (e.g., "image:/path/to/image.jpg")
            image_path = user_input.split("image:")[1].strip()
            try:
                model.image_description(image_path, session_token)
            except Exception as e:
                print(f"Error processing image: {e}")
        else:
            try:
                model.get_response(user_input, session_token)
            except Exception as e:
                print(f"Error: {e}")