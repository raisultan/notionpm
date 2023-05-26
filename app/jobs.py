from aiohttp.web import Application
from rocketry import Rocketry
from rocketry.conds import every

from app.tracker.track import track_changes_for_all


def setup_jobs(app: Application, scheduler: Rocketry) -> None:
    params = {'app': app}

    scheduler.session.create_task(
        func=track_changes_for_all,
        start_cond=every('15 seconds'),
        parameters=params,
    )
