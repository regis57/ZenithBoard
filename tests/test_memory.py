# SPDX-License-Identifier: GPL-3.0-or-later
"""`zenithboard memory` (0.34.0), against a /proc and a cgroup tree made in a temporary folder: a service's processes
added up (the social service's Python and Node together), PSS when readable and RSS otherwise, said so, the small
services counted together, what runs outside the services, and the largest processes."""
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))


def build(root, pss=True):
    proc, cg = os.path.join(root, "proc"), os.path.join(root, "cgroup")
    os.makedirs(proc)
    with open(os.path.join(proc, "meminfo"), "w") as fh:
        fh.write("MemTotal:         927000 kB\nMemFree:  100000 kB\nMemAvailable:     589000 kB\nSwapTotal:  102396 kB\nSwapFree:   102396 kB\n")
    with open(os.path.join(proc, "loadavg"), "w") as fh:
        fh.write("0.35 0.40 0.38 2/287 9999\n")
    # pid: (unit or None, name, rss kB, pss kB or None, peak kB, threads, open files)
    procs = {100: ("readsb", "readsb", 14000, 11000, 15000, 3, 12),
             200: ("zenithboard-social", "python3", 62000, 58000, 125000, 2, 9),
             201: ("zenithboard-social", "node", 40000, 36000, 41000, 7, 20),
             300: ("pfclient", "pfclient", 30000, None if not pss else 27000, 33000, 9, 30),
             400: ("cron", "cron", 900, 500, 900, 1, 5),
             500: (None, "bash", 5000, 3000, 5200, 1, 4)}
    for pid, (unit, name, rss, p, peak, threads, files) in procs.items():
        d = os.path.join(proc, str(pid))
        os.makedirs(os.path.join(d, "fd"))
        with open(os.path.join(d, "status"), "w") as fh:
            fh.write("Name:\t%s\nVmHWM:\t%d kB\nVmRSS:\t%d kB\nThreads:\t%d\n" % (name, peak, rss, threads))
        if p is not None:
            with open(os.path.join(d, "smaps_rollup"), "w") as fh:
                fh.write("Rss: %d kB\nPss: %d kB\n" % (rss, p))
        for i in range(files):
            open(os.path.join(d, "fd", str(i)), "w").close()
        if unit:
            u = os.path.join(cg, "system.slice", unit + ".service")
            os.makedirs(u, exist_ok=True)
            with open(os.path.join(u, "cgroup.procs"), "a") as fh:
                fh.write("%d\n" % pid)
    os.makedirs(os.path.join(proc, "2"))                    # a kernel thread: no VmRSS, left out
    with open(os.path.join(proc, "2", "status"), "w") as fh:
        fh.write("Name:\tkthreadd\nThreads:\t1\n")
    return proc, cg


class MemoryReportTest(unittest.TestCase):
    def run_report(self, pss=True):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        proc, cg = build(root, pss)
        import memory_report as mr
        self.addCleanup(setattr, mr, "PROC", mr.PROC)
        self.addCleanup(setattr, mr, "CGROUP", mr.CGROUP)
        mr.PROC, mr.CGROUP = proc, cg
        out = io.StringIO()
        self.assertEqual(mr.report(out), 0)
        return out.getvalue()

    def line(self, text, start):
        found = [x for x in text.splitlines() if x.strip().startswith(start)]
        self.assertTrue(found, "no line starting with %r in:\n%s" % (start, text))
        return found[0].split()

    def test_service_by_service(self):
        t = self.run_report()
        self.assertIn("Memory:   905 MB in all, 330 MB in use, 575 MB available (swap: 0 MB used of 100 MB)", t)
        self.assertIn("Threads:  287 in all. Load: 0.35 0.40 0.38", t)
        self.assertIn("memory as PSS", t)
        social = self.line(t, "zenithboard-social")
        self.assertEqual(social[1:3], ["Bluesky", "posts"])
        self.assertEqual(social[3:9], ["92", "MB", "162", "MB", "9", "29"], "Python and Node added up")
        self.assertEqual(social[9], "2")
        pf = self.line(t, "pfclient")
        self.assertEqual(pf[1:5], ["Plane", "Finder", "26", "MB"])
        self.assertIn("1 more service ", t, "cron, under 1 MB")
        lines = t.splitlines()
        order = [i for i, x in enumerate(lines) for u in ("zenithboard-social", "pfclient", "readsb") if x.strip().startswith(u)]
        self.assertEqual(order, sorted(order), "the largest first")
        self.assertEqual(self.line(t, "All services")[2:4], ["129", "MB"])
        self.assertEqual(self.line(t, "Outside the services")[-2:], ["3", "MB"])
        self.assertNotIn("run with sudo", t)
        self.assertIn("Largest processes:", t)
        self.assertNotIn("kthreadd", t)

    def test_without_root_rss_and_it_says_so(self):
        t = self.run_report(pss=False)
        self.assertIn("memory as RSS for some: run with sudo for PSS", t)
        self.assertEqual(self.line(t, "pfclient")[3:5], ["29", "MB"], "RSS: 30 000 kB")

    def test_no_cgroup_tree_still_lists_the_processes(self):
        import memory_report as mr
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        proc, _ = build(root)
        self.addCleanup(setattr, mr, "PROC", mr.PROC)
        self.addCleanup(setattr, mr, "CGROUP", mr.CGROUP)
        mr.PROC, mr.CGROUP = proc, os.path.join(root, "none")
        out = io.StringIO()
        self.assertEqual(mr.report(out), 0)
        self.assertIn("the processes alone", out.getvalue())
        self.assertIn("python3", out.getvalue())


if __name__ == "__main__":
    unittest.main()
