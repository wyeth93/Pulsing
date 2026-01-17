"""
🗣️ AI 聊天室 - 多个 AI Agent 自由对话

运行: python examples/quickstart/ai_chat_room.py

观看不同性格的 AI 们讨论一个话题！

可选参数:
  --topic "你的话题"  设置讨论话题
  --rounds 5          设置讨论轮数
"""

import argparse
import asyncio
import random
from pulsing.actor import remote, resolve
from pulsing.agent import runtime

# AI 角色配置
AI_PERSONAS = {
    "乐观派": {
        "emoji": "😊",
        "style": "总是看到事物积极的一面，用鼓励的语气说话",
        "phrases": ["我觉得这很棒！", "往好的方面想...", "这是个好机会！"],
    },
    "理性派": {
        "emoji": "🤔",
        "style": "用数据和逻辑说话，喜欢分析利弊",
        "phrases": ["从数据来看...", "逻辑上讲...", "我们需要考虑..."],
    },
    "创意派": {
        "emoji": "💡",
        "style": "喜欢跳跃性思维，提出新奇的想法",
        "phrases": ["如果我们换个角度...", "有个疯狂的想法...", "想象一下..."],
    },
    "务实派": {
        "emoji": "🔧",
        "style": "关注可行性和执行细节",
        "phrases": ["具体怎么做呢？", "实际操作中...", "落地的话..."],
    },
}


@remote
class ChatAgent:
    """聊天室中的 AI Agent"""

    def __init__(self, agent_name: str, persona: str, topic: str):
        self.agent_name = agent_name
        self.persona = persona
        self.topic = topic
        self.config = AI_PERSONAS[persona]
        self.history: list[str] = []

    def receive_message(self, from_agent: str, message: str) -> str:
        """接收其他 Agent 的消息"""
        self.history.append(f"{from_agent}: {message}")
        return "已收到"

    def generate_response(self) -> str:
        """生成回复（模拟模式）"""
        phrase = random.choice(self.config["phrases"])

        responses = [
            f"{phrase} 关于「{self.topic}」，我认为这是个值得深入探讨的话题。",
            f"{phrase} 说到这个话题，我想补充一点自己的看法。",
            f"{phrase} 听了大家的讨论，我有一些新的想法。",
            f"{phrase} 这个话题很有意思，让我想到了一些事情。",
        ]
        return random.choice(responses)

    async def speak(self, room_name: str) -> dict:
        """在聊天室发言"""
        response = self.generate_response()

        # 通知聊天室
        room = await resolve(room_name)
        await room.broadcast(self.agent_name, response)

        return {"agent": self.agent_name, "message": response}


@remote
class ChatRoom:
    """聊天室 - 协调 Agent 对话"""

    def __init__(self, topic: str):
        self.topic = topic
        self.agents: list[str] = []
        self.messages: list[dict] = []

    def join(self, agent_name: str, persona: str) -> str:
        """Agent 加入聊天室"""
        self.agents.append(agent_name)
        emoji = AI_PERSONAS[persona]["emoji"]
        print(f"  {emoji} [{agent_name}] ({persona}) 加入聊天室")
        return "欢迎加入！"

    def broadcast(self, from_agent: str, message: str) -> None:
        """广播消息"""
        persona = None
        for name in self.agents:
            if name == from_agent:
                # 找到发言者的 persona
                for p, config in AI_PERSONAS.items():
                    if name.startswith(p.replace("派", "")):
                        persona = p
                        break
                break

        emoji = AI_PERSONAS.get(persona, {}).get("emoji", "💬") if persona else "💬"
        self.messages.append({"from": from_agent, "message": message})
        print(f"\n  {emoji} [{from_agent}]: {message}")

    def get_history(self) -> list[dict]:
        """获取聊天历史"""
        return self.messages


async def main(topic: str, rounds: int):
    print("=" * 60)
    print("🗣️  AI 聊天室")
    print("=" * 60)
    print(f"\n📋 讨论话题: {topic}")
    print(f"🔄 讨论轮数: {rounds}")
    print("\n--- 参与者入场 ---\n")

    async with runtime():
        # 创建聊天室
        room = await ChatRoom.spawn(topic=topic, name="chat_room")

        # 创建不同性格的 AI Agent
        agents = []
        for persona in AI_PERSONAS.keys():
            agent_name = persona.replace("派", "") + "_AI"
            agent = await ChatAgent.spawn(
                agent_name=agent_name,
                persona=persona,
                topic=topic,
                name=agent_name,
            )
            await room.join(agent_name, persona)
            agents.append((agent_name, agent))

        print("\n--- 开始讨论 ---")

        # 进行多轮讨论
        for round_num in range(1, rounds + 1):
            print(f"\n{'─' * 40}")
            print(f"第 {round_num} 轮")
            print(f"{'─' * 40}")

            # 随机打乱发言顺序
            random.shuffle(agents)

            for agent_name, agent in agents:
                await agent.speak("chat_room")
                await asyncio.sleep(0.1)  # 模拟思考时间

        # 显示统计
        history = await room.get_history()
        print("\n" + "=" * 60)
        print("📊 讨论统计")
        print("=" * 60)
        print(f"  总发言数: {len(history)}")
        print(f"  参与者: {len(agents)} 位 AI")
        print(f"  讨论轮数: {rounds}")

    print("\n" + "=" * 60)
    print("✅ 聊天结束！")
    print("=" * 60)
    print("\n💡 提示: 修改 AI_PERSONAS 可以自定义 AI 的性格")
    print("💡 提示: 设置 OPENAI_API_KEY 后可以接入真实 LLM")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI 聊天室")
    parser.add_argument("--topic", default="人工智能会取代人类工作吗？", help="讨论话题")
    parser.add_argument("--rounds", type=int, default=3, help="讨论轮数")
    args = parser.parse_args()

    asyncio.run(main(args.topic, args.rounds))
