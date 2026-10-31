"""No developer-key model routing; manual consumer web response intake."""
from app.automation.multi_wrapper import MultiWebSessionManager, PROVIDERS
class ZeroAPIModelRouter:
    def __init__(self, sessions: MultiWebSessionManager): self.sessions=sessions
    async def generate(self,prompt:str,model_choice:str="chatgpt")->dict:
        if model_choice not in PROVIDERS: raise ValueError("Unknown model")
        return await self.sessions.prepare_prompt(model_choice,prompt)
    def record_operator_response(self,model_choice:str,response:str)->dict:
        return self.sessions.receive_operator_response(model_choice,response)
