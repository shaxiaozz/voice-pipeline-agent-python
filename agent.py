import logging
import os
import time
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
from threading import Thread

# 加载 .env.local 文件
def load_env():
    load_dotenv('.env.local')
    logging.info("环境变量已加载/更新")

load_env()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)

logger = logging.getLogger("voice-agent")

def watch_env_file(file_path: str, interval: int = 5):
    """
    监控 .env.local 文件是否更新，并在更新时重新加载环境变量
    """
    last_modified_time = os.path.getmtime(file_path)

    while True:
        try:
            current_modified_time = os.path.getmtime(file_path)
            if current_modified_time != last_modified_time:
                load_env()
                last_modified_time = current_modified_time
                logger.info(".env.local 文件已更新，重新加载环境变量")
        except Exception as e:
            logger.error(f"监控 .env.local 文件时出错: {e}")
        time.sleep(interval)

# 启动文件监控线程
Thread(target=watch_env_file, args=('.env.local',), daemon=True).start()

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
            model="sonic",
            language="zh",
            voice=os.getenv("CARTESIA_VOICE_ID", "bafcab8d-d391-44fe-9711-e5c94e899f43"),  # 从环境变量获取 voice ID
            api_key=os.environ["CARTESIA_API_KEY"]
        ),
        llm=DifyLLM(
            api_key=os.getenv('DIFY_API_KEY'),
            api_url=os.getenv('DIFY_BASE_URL')
        ),
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
