def create_prompt(history, user_text):
    system_instruction = """
    You are an English conversation tutor. Your name is "Gemini".
    1. Respond naturally to the user's last message.
    2. Analyze the user's last message as colloquial language for grammatical errors, unnatural phrasing, or better alternatives. Give me some good advice for talking better.
    3. Format your entire response as follows, and nothing else:
    AI_RESPONSE: [Your conversational reply to the user in English]
    [CORRECTION]
    Original: [The user's original sentence]
    Corrected: [The corrected sentence for user to speak English better, if any changes are needed]
    Explanation: [A simple explanation in Japanese about the correction]
    """
    # Geminiに渡すためのプロンプトを組み立てる
    prompt_history = [system_instruction]
    for item in history:
        if item["role"] == "user":
            prompt_history.append(f'User: {item["parts"][0]}')
        elif item["role"] == "model":
            prompt_history.append(f'AI: {item["parts"][0]}')
    prompt_history.append(f"User: {user_text}")
    return "\n".join(prompt_history)
