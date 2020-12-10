import unittest

from curricula_grade.dependency import topological_sort

import mock


class DependencyTests(unittest.TestCase):
    """Check topological sort."""

    def test_sort_stable(self):
        tasks = [
            mock.task("a"),
            mock.task("b")]
        topological_sort(tasks)
        self.assertEqual(len(tasks), 2)

    def test_sort_simple(self):
        tasks = [
            mock.task("b", passing={"a"}),
            mock.task("a")]
        topological_sort(tasks)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].name, "a")
        self.assertEqual(tasks[1].name, "b")

    def test_sort_diamond(self):
        tasks = [
            mock.task("d", passing={"b", "c"}),
            mock.task("c", passing={"a"}),
            mock.task("b", passing={"a"}),
            mock.task("a")]
        topological_sort(tasks)
        self.assertEqual(len(tasks), 4)
        self.assertEqual(tasks[0].name, "a")
        self.assertEqual(tasks[3].name, "d")
