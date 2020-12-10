import unittest

from curricula_grade.task.dependency import topological_sort
from curricula_grade.task.registrar import TaskRegistrar
from curricula_grade.task.collection import TaskCollection

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


class RegistrarTests(unittest.TestCase):
    """Check registration methods."""

    def test_register_manual(self):
        registrar = TaskRegistrar(TaskCollection())
        registrar[mock.Result](runnable=mock.runnable, details=dict(name="a"))
        self.assertIn("a", [task.name for task in registrar.tasks])
