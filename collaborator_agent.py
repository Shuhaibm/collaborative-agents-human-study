from json_repair import repair_json
from litellm import completion as llm_completion, batch_completion as llm_batch_completion
import copy

from prompts import agent_system_prompt,agent_system_prompt_with_user_preferences,reflective_agent_system_prompt,update_agent_notes_prompt,proper_scaffolding_prompt



class CollaboratorAgent():
    def __init__(
        self,
        model_name,
        user_preferences=None,
        agent_notes=None,
        with_scaffolding=False,
        with_proper_scaffolding=False,
        api_base=None,
        api_key=None,
        num_retries=10
    ):
        self.num_retries = num_retries
        self.model_name = model_name
        self.user_preferences = user_preferences
        self.agent_notes = agent_notes
        self.with_scaffolding = with_scaffolding
        self.with_proper_scaffolding = with_proper_scaffolding
        self.max_new_tokens = max_new_tokens = 2048
        self.kwargs = {"temperature": 1.0, "max_tokens": max_new_tokens, "timeout": 2100}
        if api_base and api_key:
            self.kwargs["api_base"] = api_base
            self.kwargs["api_key"] = api_key

        if agent_notes:
            self.system_prompt = reflective_agent_system_prompt.format(max_new_tokens=max_new_tokens, agent_notes=agent_notes)
        elif user_preferences:
            self.system_prompt = agent_system_prompt_with_user_preferences.format(max_new_tokens=max_new_tokens, user_preferences=user_preferences)
        else:
            self.system_prompt = agent_system_prompt.format(max_new_tokens=max_new_tokens)

    def get_conversation_string(self, messages):
        return "\n".join([f"{message['role'].capitalize()}: {message['content']}" for message in messages])

    def completion(self, messages):
        response = llm_completion(model=self.model_name, messages=messages, num_retries=self.num_retries, **self.kwargs).choices[0].message.content
        return response

    def add_scaffolding_to_conversation(self, messages):
        if not self.with_proper_scaffolding:
            messages[0]["content"] = f"Remember, you have been taking notes throughout past conversations about user preferences. Use whatever is relevant in these notes to guide your response:\n{self.agent_notes}" + messages[0]["content"]
            return messages
        else:
            conversation_str = self.get_conversation_string(messages)
            formatted_proper_scaffolding_prompt = proper_scaffolding_prompt.format(conversation_history=conversation_str, complete_agent_notes=self.agent_notes)
            scaffolding_messages = [{"role": "user", "content": formatted_proper_scaffolding_prompt}]

            for _ in range(self.num_retries):
                scaffolding_response = self.completion(scaffolding_messages)

                processed_scaffolding_response = repair_json(scaffolding_response, return_objects=True)
                missing_keys = [key for key in ["reasoning", "relevant_notes"] if key not in processed_scaffolding_response]
                if missing_keys:
                    print(f"Missing keys: {missing_keys}. Processed scaffolding response: {processed_scaffolding_response}")
                    continue

                scaffolded_notes = processed_scaffolding_response["relevant_notes"]
                messages[0]["content"] = f"Remember, you have been taking notes throughout past conversations about user preferences. Use these notes to guide your response:\n{scaffolded_notes}" + messages[0]["content"]

                return messages

    def generate_collaborator_response(self, conversation):
        conversation = copy.deepcopy(conversation)
        for _ in range(self.num_retries):
            if self.with_scaffolding:
                conversation = self.add_scaffolding_to_conversation(conversation)

            messages = [{"role": "system", "content": self.system_prompt}] + conversation

            response = self.completion(messages)

            processed_response = repair_json(response, return_objects=True)
            missing_keys = [key for key in ["reasoning", "response"] if key not in processed_response]
            if missing_keys:
                print(f"Missing keys: {missing_keys}. Messages: {messages}.\n\nResponse: {response}.\n\nProcessed response: {processed_response}")
                continue
            return processed_response

        print(f"Failed to generate collaborator response after {self.num_retries} retries")
        return None

    def update_agent_notes(self, agent_notes, conversation):
        conversation_str = self.get_conversation_string(conversation)
        formatted_update_agent_notes_prompt = update_agent_notes_prompt.format(agent_notes=agent_notes, conversation_str=conversation_str)

        for _ in range(self.num_retries):
            try:
                messages = [{"role": "user", "content": formatted_update_agent_notes_prompt}]
                response = self.completion(messages)
                
                processed_response = repair_json(response, return_objects=True)

                missing_keys = [key for key in ["user_preferences_reasoning", "agent_notes"] if key not in processed_response]
                if missing_keys:
                    print(f"Missing keys: {missing_keys}. Processed response: {processed_response}")
                    continue

                return processed_response
            except Exception as e:
                print(f"Failed to update agent notes: {e}")

        return None