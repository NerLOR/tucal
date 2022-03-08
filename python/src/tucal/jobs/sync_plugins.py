
import argparse

from tucal import Job
import tucal.plugins
import tucal.db


def sync_plugins(job: Job = None):
    job = job or Job()
    plugins = tucal.plugins.plugins()

    job.init('sync plugins', len(plugins), len(plugins), estimate=len(plugins) * 2)
    for course, p in plugins:
        job.begin(f'sync plugin {course} {p}')
        plugin_sync = p.sync()
        plugin_sync.sync(tucal.db.cursor())
        job.end(1)

    tucal.db.commit()
    job.end(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    sync_plugins()
