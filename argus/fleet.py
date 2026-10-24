"""Parallel, ordered execution of independent Argus jobs."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_fleet(jobs, make_harness, max_workers=4):
    """Run jobs concurrently and return reports in the original input order."""
    results = [None] * len(jobs)

    def run_one(index, job):
        started = time.perf_counter()
        try:
            report = make_harness(job["workdir"]).run(job["task"])
            return index, {
                "name": job["name"],
                "ok": True,
                "report": report,
                "seconds": round(time.perf_counter() - started, 3),
            }
        except Exception as error:
            return index, {
                "name": job["name"],
                "ok": False,
                "report": f"{type(error).__name__}: {error}",
                "seconds": round(time.perf_counter() - started, 3),
            }

    with ThreadPoolExecutor(max_workers=max(1, int(max_workers))) as executor:
        futures = [
            executor.submit(run_one, index, job)
            for index, job in enumerate(jobs)
        ]
        for future in as_completed(futures):
            index, result = future.result()
            results[index] = result
    return results
