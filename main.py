import os

import discord
from discord.ext import commands
from dotenv import load_dotenv


# =========================================================
# 환경변수 불러오기
# =========================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# 길드원 공개 페이지 주소입니다.
# 홈페이지를 외부에 배포한 뒤 .env의 WEBSITE_URL만 변경하면 됩니다.
WEBSITE_URL = os.getenv(
    "WEBSITE_URL",
    "http://127.0.0.1:5000/support",
)


# =========================================================
# 봇 설정
# =========================================================

intents = discord.Intents.default()


class SupportBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
        )

    async def setup_hook(self):
        synced_commands = await self.tree.sync()

        print(
            f"✅ 슬래시 명령어 {len(synced_commands)}개 동기화 완료"
        )

    async def on_ready(self):
        if self.user is None:
            return

        print(f"✅ 로그인 완료: {self.user}")
        print(f"✅ 지원 홈페이지 주소: {WEBSITE_URL}")


bot = SupportBot()


# =========================================================
# 홈페이지 버튼
# =========================================================

class SupportWebsiteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="지원 홈페이지 열기",
                emoji="🌐",
                style=discord.ButtonStyle.link,
                url=WEBSITE_URL,
            )
        )


# =========================================================
# /지원 명령어
# =========================================================

@bot.tree.command(
    name="지원",
    description="길드 지원 홈페이지를 확인합니다.",
)
async def support_command(
    interaction: discord.Interaction,
):
    embed = discord.Embed(
        title="🎒 길드 지원",
        description=(
            "길드 지원에 필요한 정보를 홈페이지에서 "
            "확인할 수 있습니다.\n\n"
            "💠 **코어 지원**\n"
            "코어 정보와 현재 지원 가능 수량을 확인합니다.\n\n"
            "🧙 **히든 직업 정보**\n"
            "획득 조건, 선행 퀘스트와 NPC 좌표를 확인합니다."
        ),
        color=discord.Color.from_rgb(
            120,
            150,
            255,
        ),
    )

    embed.set_footer(
        text="아래 버튼을 누르면 길드원용 지원 페이지가 열립니다."
    )

    await interaction.response.send_message(
        embed=embed,
        view=SupportWebsiteView(),
    )


# =========================================================
# 봇 실행
# =========================================================

if not DISCORD_TOKEN:
    raise RuntimeError(
        ".env 파일에 DISCORD_TOKEN이 입력되지 않았습니다."
    )

bot.run(DISCORD_TOKEN)
