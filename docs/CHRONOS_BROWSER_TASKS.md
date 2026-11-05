# Chronos browser tasks

ChatGPT, Gemini, and DeepSeek each run one task in one new browser tab. The tab closes after Exodia stores the reply. The signed-in tab stays open so the next task can open quickly without composing inside the last conversation.

A verification page is left alone. If the new tab is already on that page, Exodia does not load it again and does not inject script into it.

Image tasks for ChatGPT and Gemini return the picture with the reply. The request after `User request:` decides whether a task is an image task, so saved instructions do not hide the picture. DeepSeek does not generate images.

Task responses leave out saved instructions and per-task instructions. The settings endpoints are where saved instruction text is read and edited.
