from ..base import MultiModalAICapability
from langchain_openai import ChatOpenAI

class OpenAIAdapter(MultiModalAICapability):
    def __init__(self, api_key, model, **kwargs):
        base_url = kwargs.pop('base_url', None)
        llm_kwargs = dict(api_key=api_key, model=model, streaming=True)
        if base_url:
            llm_kwargs['base_url'] = base_url
        self.llm = ChatOpenAI(**llm_kwargs)
        self.api_key = api_key

    async def chat(self, messages, **kwargs):
        return await self.llm.ainvoke(messages)

    async def stream_chat(self, messages, **kwargs):
        async for chunk in self.llm.astream(messages):
            yield chunk

    # 如需图片生成（DALL·E），可实现如下
    def create_drawing_task(self, **kwargs):
        # 伪代码，需用 openai.Image.create
        # import openai
        # response = openai.Image.create(api_key=self.api_key, prompt=prompt, ...)
        # return response
        raise NotImplementedError("OpenAI 图片生成请用 openai.Image.create 实现")

    # 其他能力同理