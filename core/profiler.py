import functools
import logging

import yappi

log = logging.getLogger("discord.profiler")


def profile_command(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        yappi.set_clock_type("wall")
        log.info(f"⏱️  START profiling command: '{func.__name__}'")
        yappi.start()

        try:
            return await func(*args, **kwargs)
        finally:
            yappi.stop()
            stats = yappi.get_func_stats()
            stats.sort("ttot", "desc")
            top_stats = list(stats)[:5]
            log.info(f"📊 REPORT for '{func.__name__}' (Top 5 Slowest):")
            for stat in top_stats:
                full_name = stat.name
                if "/" in full_name:
                    clean_name = full_name.split("/")[-1]
                elif "\\" in full_name:
                    clean_name = full_name.split("\\")[-1]
                else:
                    clean_name = full_name

                # Log format: Time | CPU Time | Calls | Function
                log.info(
                    f" ➤ {stat.ttot:.4f}s (CPU: {stat.tsub:.4f}s) | "
                    f"Calls: {stat.ncall} | {clean_name}"
                )
            log.info("------------------------------------------------")
            yappi.clear_stats()

    return wrapper
