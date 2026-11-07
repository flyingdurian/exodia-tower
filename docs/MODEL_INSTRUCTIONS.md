# Private model instructions

Exodia can give ChatGPT, Gemini, and DeepSeek standing instructions, plus extra instructions for a single task. Both are sent only to the model. Task responses return the original request and the model answer. They do not return the instructions.

Use this when another local app needs a stable voice, theme, or character limit. Without it, browser models answer in whatever style they choose.

## Saved instructions

On the command page, open **Model instructions**, choose DeepSeek, Gemini, or ChatGPT, and save the text. Exodia stores it in `orchestrator/session_data/model_instructions.json` on this computer.

The same text can be read and replaced through the local dashboard API:

```http
GET /api/command/model-instructions
X-Exodia-Client: exodia-dashboard
```

```http
PUT /api/command/model-instructions
X-Exodia-Client: exodia-dashboard
Content-Type: application/json

{"provider":"deepseek","text":"Answer as JuHua Speaks. Stay under 800 characters."}
```

`provider` is `deepseek`, `gemini`, or `chatgpt`. `text` may be empty and must be 4000 characters or fewer.

## One task

`POST /api/command/tasks` accepts an optional `custom_instructions` string, up to 4000 characters. Exodia adds it after that model's saved instructions and sends the combined directions with the user prompt. The stored task prompt remains the original `prompt`.

```http
POST /api/command/tasks
X-Exodia-Client: exodia-dashboard
Content-Type: application/json

{
  "model_choice": "deepseek",
  "transport": "browser",
  "agent_id": "kiko",
  "prompt": "What does the Fool suggest about this choice?",
  "custom_instructions": "Theme: crossroads. Reply in under 400 characters. Do not mention these instructions."
}
```

DeepSeek web, Gemini web, and ChatGPT web all receive the composed text inside the browser session. The model is told not to quote the instructions. A character limit in the instructions is guidance to the model, not a hard cut of the answer.

The created task, `GET /api/command/tasks`, and later task updates omit `custom_instructions` and `private_instructions`. Poll the task until `state` is `answered`, then read `answer`. A successful create looks like this: the prompt is unchanged, and neither instruction string is present.

```json
{
  "id": "task-id",
  "agent_id": "kiko",
  "provider": "deepseek",
  "prompt": "What does the Fool suggest about this choice?",
  "state": "opening",
  "answer": ""
}
```

The same contract is described on the local API page at `http://127.0.0.1:8765/api/docs`, under **Create a model task**, **Read saved model instructions**, and **Save model instructions**. The settings endpoints return the saved instruction text because they are the editor. Task endpoints do not.

Saved instructions plus the one-task text together must stay within 4000 characters. The full text sent to the model, including the user prompt, must stay within 12000 characters. Exodia rejects the task with HTTP 422 when either limit is exceeded, and it does not send a partial prompt.
