"""Handler for the /status command — shows status of all agents."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from tgbot.services.backend_client import BackendClient

logger = logging.getLogger(__name__)


def _format_uptime(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    s = int(seconds)
    if s < 60:
        return f"{s}с"
    elif s < 3600:
        m, sec = divmod(s, 60)
        return f"{m}м {sec}с"
    elif s < 86400:
        h, m = divmod(s // 60, 60)
        return f"{h}ч {m}м"
    else:
        d, h = divmod(s // 3600, 24)
        return f"{d}д {h}ч"


def _format_table(agents: list[dict]) -> str:
    col1, col2, col3 = 16, 10, 10
    header = f"{'Agent':<{col1}}{'Ver':<{col2}}{'Uptime':<{col3}}"
    sep = "─" * (col1 + col2 + col3)
    rows = [header, sep]
    for agent in agents:
        reachable = agent.get("status") == "ok"
        name = agent.get("name", "?")
        ver = agent.get("version", "—") if reachable else "—"
        uptime = _format_uptime(agent.get("uptime_seconds")) if reachable else "—"
        rows.append(f"{name:<{col1}}{ver:<{col2}}{uptime:<{col3}}")
    return "\n".join(rows)


def make_status_handler(backend_client: BackendClient):
    """Return a /status command handler bound to the given backend_client."""

    async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None:
            return
        try:
            data = await backend_client.get_agents_status()
            agents = data.get("agents", [])
            table = _format_table(agents)
            text = f"<b>Статус агентов</b>\n\n<pre>{table}</pre>"
            await update.message.reply_text(text, parse_mode="HTML")
        except Exception as e:
            logger.warning("Failed to fetch agents status: %s", e)
            await update.message.reply_text("Не удалось получить статус агентов")

    return status_command
