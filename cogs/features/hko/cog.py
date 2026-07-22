import logging
from dataclasses import dataclass
from datetime import datetime, date

import aiohttp
import discord
from discord.ext import commands, tasks

from core.config import settings
from core.iam import is_owner, not_blacklisted
from core.ui import UI

logger = logging.getLogger("bot.hko")

"""
Documentation: https://www.hko.gov.hk/tc/weatherAPI/doc/files/HKO_Open_Data_API_Documentation_tc.pdf
API endpoint: https://data.weather.gov.hk/weatherAPI/opendata/weather.php
Method: GET
Returns: JSON
"""
HKO_CURRENT_WEATHER_URL = (
    "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=rhrread&lang=tc"
)
HKO_FORECAST_URL = (
    "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=fnd&lang=tc"
)
HKO_LOCAL_FORECAST_URL = (
    "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=flw&lang=tc"
)
HKO_WEATHER_ICON_URL = "https://www.hko.gov.hk/images/wxicon/pic{code}.png"

@dataclass
class WeatherSnapshot:
    temp_c: float | None
    warning_text: str

class HKO(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None
        self.alert_channel_id = settings.HKO_ALERT_CHANNEL_ID
        self.last_snapshot: WeatherSnapshot | None = None
        self.scheduled_report_time: tuple[int, int] | None = None
        self.last_scheduled_report_date: date | None = None

    """
    Create a HTTP session and start the weather watch loop.
    This is not related to admin/management.py !load commands.
    """
    async def cog_load(self):
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
        self.sudden_weather_watch.start()
        logger.info("🌦️ HKO feature loaded.")

    """
    Cancel the weather watch loop and close the HTTP session.
    This is not related to admin/management.py !load commands.
    """
    async def cog_unload(self):
        self.sudden_weather_watch.cancel()
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("🌦️ HKO feature unloaded.")

    """
    Fetch current weather JSON from HKO endpoint.
    """
    async def _fetch_current_weather(self) -> dict:
        if self.session is None:
            raise RuntimeError("HTTP session is not initialized.")

        async with self.session.get(HKO_CURRENT_WEATHER_URL) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _fetch_nine_day_forecast(self) -> dict:
        if self.session is None:
            raise RuntimeError("HTTP session is not initialized.")

        async with self.session.get(HKO_FORECAST_URL) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _fetch_local_forecast(self) -> dict:
        if self.session is None:
            raise RuntimeError("HTTP session is not initialized.")

        async with self.session.get(HKO_LOCAL_FORECAST_URL) as resp:
            resp.raise_for_status()
            return await resp.json()

    """
    Extract HK temperature from payload.
    """
    @staticmethod
    def _extract_temperature(payload: dict) -> float | None:
        temp_block = payload.get("temperature", {})
        if not isinstance(temp_block, dict):
            return None
        temp_data = temp_block.get("data", [])
        if not isinstance(temp_data, list):
            return None
        if not temp_data:
            return None

        # Prefer Hong Kong Observatory station; fallback to first station.
        for row in temp_data:
            place = str(row.get("place", "")).lower()
            if "hong kong observatory" in place or "香港天文台" in place:
                value = row.get("value")
                return float(value) if value is not None else None

        value = temp_data[0].get("value")
        return float(value) if value is not None else None

    """
    Extract warning text from payload.
    """
    @staticmethod
    def _extract_warning_text(payload: dict) -> str:
        messages = payload.get("warningMessage", [])
        if isinstance(messages, str):
            return messages.strip()
        if not isinstance(messages, list) or not messages:
            return ""
        return " | ".join(str(item).strip() for item in messages if str(item).strip())

    """
    Extract rainfall summary from payload.
    """
    @staticmethod
    def _extract_rainfall_summary(payload: dict) -> str | None:
        rainfall_block = payload.get("rainfall", {})
        if not isinstance(rainfall_block, dict):
            return None
        rainfall_data = rainfall_block.get("data", [])
        if not isinstance(rainfall_data, list):
            return None
        if not rainfall_data:
            return None

        rainy_amounts = []
        for row in rainfall_data:
            max_val = row.get("max")
            if isinstance(max_val, (int, float)) and max_val > 0:
                rainy_amounts.append(float(max_val))

        if not rainy_amounts:
            return None

        avg_amount = sum(rainy_amounts) / len(rainy_amounts)
        return f"{avg_amount:.1f} mm"

    """
    Extract PSR from forecast payload.
    """
    @staticmethod
    def _extract_psr_from_forecast(payload: dict) -> str | None:
        forecast_rows = payload.get("weatherForecast", [])
        if not isinstance(forecast_rows, list):
            return None
        if not forecast_rows:
            return None

        first = forecast_rows[0]
        psr = str(first.get("PSR", "")).strip()
        if not psr:
            return None

        return psr

    """
    Extract local forecast from payload.
    """
    @staticmethod
    def _extract_local_forecast(payload: dict) -> tuple[str, str] | None:
        period = str(payload.get("forecastPeriod", "")).strip()
        desc = str(payload.get("forecastDesc", "")).strip()
        if not period or not desc:
            return None
        return period, desc

    """
    Convert payload to WeatherSnapshot.
    """
    def _to_snapshot(self, payload: dict) -> WeatherSnapshot:
        return WeatherSnapshot(
            temp_c=self._extract_temperature(payload),
            warning_text=self._extract_warning_text(payload),
        )

    """
    Format ISO datetime from HKO into local-friendly HKT label.
    """
    @staticmethod
    def _format_update_time(raw: str) -> str:
        try:
            dt = datetime.fromisoformat(raw)
            return dt.strftime("%Y年 %m月 %d日 %H:%M:%S HKT")
        except (TypeError, ValueError):
            return raw

    """
    Parse time string into tuple of (hour, minute).
    """
    @staticmethod
    def _parse_time_hhmm(raw: str) -> tuple[int, int] | None:
        raw = raw.strip()
        parts = raw.split(":", 1)
        if len(parts) != 2:
            return None

        hh_str, mm_str = parts
        if not (hh_str.isdigit() and mm_str.isdigit()):
            return None

        hh = int(hh_str)
        mm = int(mm_str)
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            return None

        return hh, mm

    """
    Format hour and minute into HH:MM format.
    """
    @staticmethod
    def _format_hhmm(hour: int, minute: int) -> str:
        return f"{hour:02d}:{minute:02d} HKT"

    """
    Build a weather embed from payload.
    """
    def _build_weather_embed(
        self,
        payload: dict,
        *,
        psr_text: str | None = None,
        rainfall_text: str | None = None,
        local_forecast: tuple[str, str] | None = None,
    ) -> discord.Embed:
        temp = self._extract_temperature(payload)
        humidity_block = payload.get("humidity", {})
        humidity = humidity_block.get("data", []) if isinstance(humidity_block, dict) else []
        if not isinstance(humidity, list):
            humidity = []

        uv_block = payload.get("uvindex", {})
        uv_data = uv_block.get("data", []) if isinstance(uv_block, dict) else []
        if not isinstance(uv_data, list):
            uv_data = []

        icon = payload.get("icon", [])
        if not isinstance(icon, list):
            icon = []
        update_time = payload.get("updateTime", "Unknown")
        warning_text = self._extract_warning_text(payload)

        humidity_val = humidity[0].get("value") if humidity else None
        uv_val = uv_data[0].get("value") if uv_data else None

        embed = discord.Embed(
            title="🌦️ 現時天氣",
            color=discord.Color.blue(),
            description=f"Updated: `{self._format_update_time(update_time)}`",
        )
        embed.add_field(
            name="氣溫",
            value=f"{temp:.1f}°C" if temp is not None else "N/A",
            inline=True,
        )
        embed.add_field(
            name="溫度",
            value=f"{humidity_val}%" if humidity_val is not None else "N/A",
            inline=True,
        )
        embed.add_field(
            name="紫外線指數",
            value=str(uv_val) if uv_val is not None else "N/A",
            inline=True,
        )
        if psr_text:
            embed.add_field(name="降雨概率", value=psr_text, inline=True)
        if rainfall_text:
            embed.add_field(name="平均雨量", value=rainfall_text, inline=True)
        if icon:
            code = icon[0]
            embed.set_thumbnail(url=HKO_WEATHER_ICON_URL.format(code=code))
        if local_forecast:
            period, desc = local_forecast
            forecast_text = f"```text\n{desc[:1000]}\n```"
            embed.add_field(name=period[:256], value=forecast_text, inline=False)
        if warning_text:
            warning_text = f"```text\n{warning_text[:1000]}\n```"
            embed.add_field(name="天氣警告", value=warning_text, inline=False)

        return embed

    """
    Build a report embed from payload.
    """
    async def _build_report_embed_from_payload(self, payload: dict) -> discord.Embed:
        rainfall_text = self._extract_rainfall_summary(payload)
        psr_text = None
        local_forecast = None

        try:
            forecast_payload = await self._fetch_nine_day_forecast()
            psr_text = self._extract_psr_from_forecast(forecast_payload)
        except Exception as e:  # pragma: no cover - runtime/network path
            logger.warning(f"HKO forecast fetch failed: {e}")

        try:
            local_forecast_payload = await self._fetch_local_forecast()
            local_forecast = self._extract_local_forecast(local_forecast_payload)
        except Exception as e:  # pragma: no cover - runtime/network path
            logger.warning(f"HKO local forecast fetch failed: {e}")

        return self._build_weather_embed(
            payload,
            psr_text=psr_text,
            rainfall_text=rainfall_text,
            local_forecast=local_forecast,
        )

    """
    Send a scheduled report to the alert channel.
    """
    async def _send_scheduled_report(self, payload: dict):
        if not self.alert_channel_id:
            return

        channel = self.bot.get_channel(self.alert_channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(self.alert_channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                logger.warning("HKO alert channel is invalid or inaccessible.")
                return

        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            logger.warning("HKO alert channel is not a text channel.")
            return

        embed = await self._build_report_embed_from_payload(payload)
        await channel.send(embed=embed)

    """
    Detect changes between two WeatherSnapshots.
    """
    def _detect_changes(self, prev: WeatherSnapshot, curr: WeatherSnapshot) -> list[str]:
        changes: list[str] = []
        prev_items = {item.strip() for item in prev.warning_text.split("|") if item.strip()}
        curr_items = {item.strip() for item in curr.warning_text.split("|") if item.strip()}
        added_items = sorted(curr_items - prev_items)

        if added_items:
            added_text = "\n".join(f"- {item}" for item in added_items)
            changes.append(f"⚠️ New weather warning(s):\n{added_text}")

        return changes

    """
    Send an alert to the alert channel.
    """
    async def _send_alert(self, changes: list[str]):
        if not self.alert_channel_id:
            return

        channel = self.bot.get_channel(self.alert_channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(self.alert_channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                logger.warning("HKO alert channel is invalid or inaccessible.")
                return

        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            logger.warning("HKO alert channel is not a text channel.")
            return

        embed = discord.Embed(
            title="🚨 Sudden Weather Change",
            description="\n".join(changes)[:4096],
            color=discord.Color.orange(),
        )
        await channel.send(embed=embed)


    """
    Routine function for watching sudden weather changes and sending alerts.
    """
    @tasks.loop(minutes=settings.HKO_ALERT_INTERVAL_MINUTES)
    async def sudden_weather_watch(self):
        if not self.alert_channel_id:
            return

        try:
            payload = await self._fetch_current_weather()
        except Exception as e:  # pragma: no cover - runtime/network path
            logger.warning(f"HKO watch fetch failed: {e}")
            return

        now = datetime.now()
        today = now.date()
        if self.scheduled_report_time is not None:
            target_hour, target_minute = self.scheduled_report_time
            current_minutes = now.hour * 60 + now.minute
            target_minutes = target_hour * 60 + target_minute
            if current_minutes >= target_minutes and self.last_scheduled_report_date != today:
                await self._send_scheduled_report(payload)
                self.last_scheduled_report_date = today

        current = self._to_snapshot(payload)
        if self.last_snapshot is None:
            self.last_snapshot = current
            return

        changes = self._detect_changes(self.last_snapshot, current)
        self.last_snapshot = current

        if changes:
            await self._send_alert(changes)

    """
    Wait for the bot to be ready before starting the weather watch loop.
    """
    @sudden_weather_watch.before_loop
    async def before_weather_watch(self):
        await self.bot.wait_until_ready()

    """ 
    Command to get latest Hong Kong weather summary from HKO.
    """
    @commands.command(name="weather")
    @not_blacklisted()
    async def weather(self, ctx):
        try:
            payload = await self._fetch_current_weather()
        except Exception as e:  # pragma: no cover - runtime/network path
            logger.warning(f"HKO command fetch failed: {e}")
            return await ctx.send(embed=UI.error("Weather Error", "Failed to fetch HKO data."))
        await ctx.send(embed=await self._build_report_embed_from_payload(payload))

    """
    Command to set the channel for sudden weather alerts.
    """
    @commands.command(name="sethkochannel", hidden=True)
    @is_owner()
    async def set_hko_channel(self, ctx):
        self.alert_channel_id = ctx.channel.id
        self.last_snapshot = None
        await ctx.send(embed=UI.success("HKO Alerts", f"Alert channel set to {ctx.channel.mention}."))

    """
    Command to unset the channel for sudden weather alerts.
    """
    @commands.command(name="unsethkochannel", hidden=True)
    @is_owner()
    async def unset_hko_channel(self, ctx):
        self.alert_channel_id = None
        self.scheduled_report_time = None
        self.last_scheduled_report_date = None
        self.last_snapshot = None
        await ctx.send(embed=UI.info("HKO Alerts", "Alert channel unset and HKO time cleared."))

    """
    Command to set the time for scheduled reports.
    """
    @commands.command(name="sethkotime", hidden=True)
    @is_owner()
    async def set_hko_time(self, ctx, hhmm: str):
        if not self.alert_channel_id:
            return await ctx.send(
                embed=UI.warn("HKO Time", "Set channel first with `!sethkochannel` in target channel.")
            )

        parsed = self._parse_time_hhmm(hhmm)
        if parsed is None:
            return await ctx.send(embed=UI.warn("HKO Time", "Invalid format. Use `HH:MM` (24-hour)."))

        self.scheduled_report_time = parsed
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute
        target_minutes = parsed[0] * 60 + parsed[1]
        self.last_scheduled_report_date = now.date() if current_minutes >= target_minutes else None

        await ctx.send(
            embed=UI.success(
                "HKO Time",
                f"Daily scheduled report time set to `{self._format_hhmm(*parsed)}`.",
            )
        )

    """
    Command to unset the time for scheduled reports.
    """
    @commands.command(name="unsethkotime", hidden=True)
    @is_owner()
    async def unset_hko_time(self, ctx):
        self.scheduled_report_time = None
        self.last_scheduled_report_date = None
        await ctx.send(embed=UI.info("HKO Time", "Scheduled report time cleared."))

    """
    Command to show HKO watcher status and alert destination channel.
    """
    @commands.command(name="hkostatus")
    @not_blacklisted()
    async def hko_status(self, ctx):
        """Show HKO watcher status and alert destination channel."""
        channel_text = (
            f"<#{self.alert_channel_id}>" if self.alert_channel_id else "Not configured"
        )
        time_text = (
            self._format_hhmm(*self.scheduled_report_time)
            if self.scheduled_report_time is not None
            else "Not configured"
        )
        await ctx.send(
            embed=UI.info(
                "HKO Status",
                f"Watcher running: `{self.sudden_weather_watch.is_running()}`\n"
                f"Alert channel: {channel_text}\n"
                f"Scheduled report time: {time_text}",
            )
        )


async def setup(bot):
    await bot.add_cog(HKO(bot))
