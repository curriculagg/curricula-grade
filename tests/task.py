import unittest

from curricula_grade.grader.task.dependency import topological_sort
from curricula_grade.grader.task.registrar import TaskRegistrar
from curricula_grade.grader.task.collection import TaskCollection
from curricula_grade.grader.task.filter import filter_tasks
from curricula_grade.resource import Context
from curricula_grade.exception import GraderException
from curricula_grade.grader.task import *

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

    def setUp(self):
        self.registrar = TaskRegistrar()

    def test_register_manual(self):
        self.registrar.register(runnable=mock.runnable, details=dict(name="a"), result_type=mock.MockResult)
        self.assertIn("a", [task.name for task in self.registrar.tasks])

    def test_brackets(self):
        self.registrar[mock.MockResult](mock.runnable, name="a")
        self.assertIn("a", [task.name for task in self.registrar.tasks])

    def test_annotation(self):
        self.registrar(mock.runnable, name="a")
        self.assertIn("a", [task.name for task in self.registrar.tasks])

    def test_decorator_brackets(self):
        @self.registrar[mock.MockResult](name="a")
        def a():
            return mock.MockResult()
        self.assertIn("a", [task.name for task in self.registrar.tasks])

    def test_decorator_annotation(self):
        @self.registrar(name="a")
        def a() -> mock.MockResult:
            return mock.MockResult()
        self.assertIn("a", [task.name for task in self.registrar.tasks])

    def test_no_type(self):
        self.assertRaises(GraderException, lambda: self.registrar(lambda: mock.MockResult(), name="test"))


class CollectionTests(unittest.TestCase):
    """Basic behavior."""

    def setUp(self):
        self.collection = TaskCollection()

    def test_push(self):
        self.collection.push(mock.task("a"))
        self.assertIn("a", [task.name for task in self.collection])

    def test_push_duplicate(self):
        self.collection.push(mock.task("a"))
        self.assertRaises(GraderException, lambda: self.collection.push(mock.task("a")))


class FilterTests(unittest.TestCase):
    """Check if the filter works."""

    def setUp(self):
        self.collection = TaskCollection()
        self.collection.push(mock.task("a", tags={"t1", "t2"}))
        self.collection.push(mock.task("b", passing={"a"}))
        self.collection.push(mock.task("c", passing={"a"}))
        self.collection.push(mock.task("d", passing={"b"}))
        self.collection.push(mock.task("e", tags={"t2"}))

    def test_filter_names_empty(self):
        context = Context(options=dict(), task_names={"z"})
        self.assertEqual(
            set(),
            filter_tasks(context=context, problem_short="p", tasks=self.collection))

    def test_filter_names_single(self):
        context = Context(options=dict(), task_names={"a"})
        self.assertEqual(
            {"a"},
            filter_tasks(context=context, problem_short="p", tasks=self.collection))

    def test_filter_names_multiple(self):
        context = Context(options=dict(), task_names={"a", "b"})
        self.assertEqual(
            {"a", "b"},
            filter_tasks(context=context, problem_short="p", tasks=self.collection))

    def test_filter_names_all(self):
        context = Context.from_options(dict(tasks=("p:*",)))
        self.assertEqual(
            {"a", "b", "c", "d", "e"},
            filter_tasks(context=context, problem_short="p", tasks=self.collection))

    def test_filter_names_dependencies(self):
        context = Context(options=dict(), task_names={"d"})
        self.assertEqual(
            {"a", "b", "d"},
            filter_tasks(context=context, problem_short="p", tasks=self.collection))

    def test_filter_tags_single(self):
        context = Context(options=dict(), task_tags={"t1"})
        self.assertEqual(
            {"a"},
            filter_tasks(context=context, problem_short="p", tasks=self.collection))

    def test_filter_tags_multiple(self):
        context = Context(options=dict(), task_tags={"t2"})
        self.assertEqual(
            {"a", "e"},
            filter_tasks(context=context, problem_short="p", tasks=self.collection))

    def test_filter_names_and_tags(self):
        context = Context(options=dict(), task_names={"e"}, task_tags={"t1"})
        self.assertEqual(
            {"a", "e"},
            filter_tasks(context=context, problem_short="p", tasks=self.collection))


class SerializationTests(unittest.TestCase):
    """Check model serialization and deserialization."""

    def test_message(self):
        message = Message(kind=Message.Kind.DEBUG, content="test")
        self.assertEqual(message, Message.load(message.dump()))

    def test_error(self):
        error = Error(
            description="Hello, world!",
            suggestion="Try this...",
            location="Here",
            traceback="Blah blah blah",
            expected=object(),
            actual=object(),)
        self.assertEqual(error, Error.load(error.dump()))

    def test_error_empty(self):
        error = Error(description="Hello, world!")
        self.assertEqual(error, Error.load(error.dump()))

    def test_result(self):
        task = mock.task("task")
        result = Result(
            complete=True,
            passing=False,
            score=1,
            error=Error(description="Test failed!"),
            messages=[Message(kind=Message.Kind.DEBUG, content="test")],
            details={"key": "value"})
        result.task = task
        self.assertEqual(result, Result.load(result.dump(), task))

    def test_result_empty(self):
        task = mock.task("task")
        result = Result(complete=True, passing=False)
        result.task = task
        self.assertEqual(result, Result.load(result.dump(), task))
