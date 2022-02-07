
import argparse

from tucal import Job
import tucal.plugins


def sync_plugins(job: Job = None):
    job = job or Job()
    plugins = tucal.plugins.plugins()

    job.init('sync plugins', len(plugins), len(plugins), estimate=len(plugins) * 2)
    for course, p in plugins:
        job.begin(f'sync plugin {course} {p}')
        p.sync()
        job.end(1)
    job.end(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    sync_plugins()
