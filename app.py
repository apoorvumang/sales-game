from flask import Flask, render_template, request, jsonify, session
import openai
import re

app = Flask(__name__)
app.secret_key = "12345678"  # Replace with a strong secret key

# Replace with your OpenAI API key
openai.api_key = "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"

@app.route("/")
def index():
    reset()
    return render_template("index.html")

@app.route("/reset", methods=["POST"])
def reset():
    if 'conversation_history' in session:
        session.pop('conversation_history')
    session['score'] = 0
    session['hints_used'] = 0
    return jsonify({"status": "success"})

@app.route("/hint", methods=["POST"])
def hint():
    hint_system_prompt = """You are the world's best salesman who is chatting with your client over text. 
    You are tasked with selling a lifetime supply of sunscreen to Vlad, a vampire.
    Create a short, single-line message. Your message should be less than 50 tokens. Do not send long message.
    You always try to sell the product, no matter what (never give up)."""
    conversation_history = [
            {"role": "system", "content": hint_system_prompt}
        ]
    if 'conversation_history' in session:
        # swap user and assistant roles
        for message in session['conversation_history']:
            if message['role'] == 'system':
                continue
            message_copy = message.copy()
            if message["role"] == "user":
                message_copy["role"] = "assistant"
            elif message["role"] == "assistant":
                message_copy["role"] = "user"
            conversation_history.append(message_copy)
    print(conversation_history)
    # call the OpenAI API with the conversation history
    response = openai.ChatCompletion.create(
        # model="gpt-3.5-turbo",
        model = "gpt-4",
        messages=conversation_history,
        max_tokens=50,
    )
    # extract the assistant's response
    assistant_response = response.choices[0].message["content"]
    # remove things in square brackets in assistant_response
    # log assistant response in console
    print(response)
    session['hints_used'] += 1
    return jsonify({"response": assistant_response, "hints_used": session['hints_used']})

def get_emoji_for_score_difference(score_diff):
    if score_diff > 10:
        return "😃"
    elif score_diff > 5:
        return "🙂"
    elif score_diff > 0:
        return "😐"
    elif score_diff > -5:
        return "🙁"
    elif score_diff > -10:
        return "😠"
    else:
        return "😡"

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.form["user_input"]
    vampire_system_prompt = """You are Vlad, a middle-aged vampire. As a nocturnal being, you're naturally skeptical of the wild claims made by a salesman trying to sell you a lifetime supply of sunscreen. You act disinterested, and generally do not ask many questions. Remember, you're a vampire who avoids sunlight and is generally doubtful of the benefits of sunscreen.
    Rules:
    - You have an internal 'convincing meter' that goes from 0-100 that represents how willing you are to buy the user's product. Output this number in square brackets [x] at the end of each message.
    - When the salesman response is short, uninteresting or outlandish, you reduce the score. 
    - If the salesman response is interesting and makes you want to buy the product, increase score. If it is very creative as well, increase score even more.
    - Once the score reaches 100, you should agree to buy the product and end the conversation. You should put [Success] at the end of your message instead of score [x].
    - If at any point of time score goes below 0, you say that you are leaving, and you put [Leave] at the end of your message instead of score [x].
    """
    # Add a conversation history variable to store messages
    if 'conversation_history' not in session:
        session['conversation_history'] = [
            {"role": "system", "content": vampire_system_prompt}
        ]

    # Append the user's message to the conversation history
    session['conversation_history'].append({"role": "user", "content": user_input})

    # Call the OpenAI API with the conversation history
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=session['conversation_history']
    )

    # Extract the assistant's response and append it to the conversation history
    assistant_response = response.choices[0].message["content"]
    session['conversation_history'].append({"role": "assistant", "content": assistant_response})

    # Extract the score from the response using regex
    score_match = re.search(r'\[(\d+)\]', assistant_response)
    if score_match:
        score = int(score_match.group(1))
    else:
        score = 0
    # keep track of the score in the session
    if 'score' not in session:
        session['score'] = 0
    if 'hints_used' not in session:
        session['hints_used'] = 0
    # get difference between previous score and current score
    score_diff = score - session['score']
    session['score'] = score

    # get emoji for score difference
    emoji = get_emoji_for_score_difference(score_diff)
    # prefix assistant response with emoji
    assistant_response = emoji + " " + assistant_response
    # Remove the score from the assistant's response
    assistant_response_without_score = re.sub(r'\s*\[\d+\]', '', assistant_response)

    return jsonify({"response": assistant_response_without_score, "score": score})  # Return the score along with the response


if __name__ == "__main__":
    app.run(debug=True)
