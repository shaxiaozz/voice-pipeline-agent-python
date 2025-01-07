import logging
import os
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, silero, cartesia
from dify_llm import DifyLLM

load_dotenv('.env.local')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)

logger = logging.getLogger("voice-agent")

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

def setup_agent_events(agent: VoicePipelineAgent):
    @agent.on("speech_started")
    def on_speech_started():
        print("\n用户开始说话...")

    @agent.on("speech_ended")
    def on_speech_ended():
        print("用户停止说话")

    @agent.on("transcribing")
    def on_transcribing(partial):
        print(f"\r正在识别: {partial}", end='', flush=True)

    @agent.on("thinking")
    def on_thinking():
        print("\n正在思考...")

    @agent.on("speaking")
    def on_speaking():
        print("\n正在回答...")

    @agent.on("error")
    def on_error(error):
        print(f"\n错误: {error}")

async def entrypoint(ctx: JobContext):
    logger.info(f"正在连接房间: {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()
    logger.info(f"为参与者 {participant.identity} 启动语音助手")

    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=openai.STT(language="zh"),
        tts=cartesia.TTS(
            model="sonic-multilingual",
            language="zh",
            voice="bafcab8d-d391-44fe-9711-e5c94e899f43",
            api_key=os.environ["CARTESIA_API_KEY"]
        ),
        #llm=openai.LLM(
            #base_url="http://localhost:11438/v1",
            #model="Hermes-3-Llama-3.1-405B"),
            #model="gpt-4o"),
        llm=DifyLLM(api_key=os.getenv('DIFY_API_KEY'),api_url=os.getenv('DIFY_BASE_URL')),
    )

    # 设置事件监听器
    setup_agent_events(agent)

    agent.start(ctx.room, participant)
    logger.info("语音助手启动成功")

    try:
        # 根据 AGENT_NAME 选择不同的问候语
        greeting = {
            "lawyer": "你好！我是张雨婷，很高兴为你解答法律相关的问题!",
            "stewardess": "我是你的空姐朱莉娅。请问有什么我可以帮到你的吗？"
        }.get(os.getenv('AGENT_NAME', 'default_agent'))
        
        if greeting:
            await agent.say(greeting, allow_interruptions=True)
            logger.info("发送初始问候")
        else:
            logger.warning(f"未知的 AGENT_NAME: {os.getenv('AGENT_NAME')}")
            
    except Exception as e:
        logger.error(f"初始问候发送失败: {e}")

if __name__ == "__main__":
    agent_name = os.getenv('AGENT_NAME', 'default_agent')
    logger.info(f"启动Agent: {agent_name}")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=agent_name,
            prewarm_fnc=prewarm,
        ),
    )
