import discord
from discord import app_commands
from discord.ext import commands


# =========================================================
# 홈페이지 주소
# =========================================================

# 나중에 홈페이지를 배포하면 이 주소를 바꿔주세요.
WEBSITE_URL = "http://127.0.0.1:5000"

CORE_URL = f"{WEBSITE_URL}/cores"
HIDDEN_JOB_URL = f"{WEBSITE_URL}/hidden-jobs"


# =========================================================
# 홈페이지 이동 버튼
# =========================================================

class WebsiteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        core_button = discord.ui.Button(
            label="코어 도감",
            emoji="💠",
            style=discord.ButtonStyle.link,
            url=CORE_URL,
        )

        hidden_job_button = discord.ui.Button(
            label="히든 직업",
            emoji="🧙",
            style=discord.ButtonStyle.link,
            url=HIDDEN_JOB_URL,
        )

        self.add_item(core_button)
        self.add_item(hidden_job_button)


# =========================================================
# 도감 명령어
# =========================================================

class WebsiteCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="티타임",
        description="코어와 히든 직업 도감 홈페이지를 확인합니다.",
    )
    async def encyclopedia(
        self,
        interaction: discord.Interaction,
    ):
        embed = discord.Embed(
            title="세레스온라인 길드 티타임 지원 및 정보",
            description=(
                "아래 버튼을 눌러 원하는 정보를 확인해주세요.\n\n"
                "💠 **코어 도감**\n"
                "코어 효과와 보유 수량을 확인할 수 있습니다.\n\n"
                "🧙 **히든 직업**\n"
                "획득 조건, 선행 퀘스트와 NPC 좌표를 "
                "확인할 수 있습니다."
            ),
            color=discord.Color.from_rgb(
                115,
                137,
                218,
            ),
        )

        embed.set_footer(
            text="버튼을 누르면 홈페이지가 열립니다."
        )

        await interaction.response.send_message(
            embed=embed,
            view=WebsiteView(),
        )


# =========================================================
# Cog 등록
# =========================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(
        WebsiteCog(bot)
    )