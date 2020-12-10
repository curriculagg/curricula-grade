import unittest

from curricula_grade.grader.task.dependency import topological_sort
from curricula_grade.grader.task.registrar import TaskRegistrar
from curricula_grade.grader.task.collection import TaskCollection
from curricula_grade.exception import GraderException

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
        registrar(runnable=mock.runnable, details=dict(name="a"), result_type=mock.MockResult)
        self.assertIn("a", [task.name for task in registrar.tasks])

    def test_sugared(self):
        registrar = TaskRegistrar(TaskCollection())
        registrar[mock.Mock](mock.runnable, name="a")
        self.assertIn("a", [task.name for task in registrar.tasks])

    def test_decorator(self):
        registrar = TaskRegistrar(TaskCollection())

        @registrar[mock.Mock](name="a")
        def a():
            return mock.MockResult()

        self.assertIn("a", [task.name for task in registrar.tasks])


class CollectionTests(unittest.TestCase):
    """Basic behavior."""

    def test_push(self):
        collection = TaskCollection()
        collection.push(mock.task("a"))
        self.assertIn("a", [task.name for task in collection])

    def test_push_duplicate(self):
        collection = TaskCollection()
        collection.push(mock.task("a"))
        self.assertRaises(GraderException, lambda: collection.push(mock.task("a")))


class FilterTests(unittest.TestCase):
    """Check if the filter works."""


