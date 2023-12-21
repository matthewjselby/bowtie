# type: ignore[reportMissingParameterType]
"""
Hypothesis strategies and support for Bowtie.

Note that this module depends on you having installed Hypothesis.
"""

from string import printable

from attrs import asdict
from hypothesis.strategies import (
    booleans,
    builds,
    composite,
    dictionaries,
    fixed_dictionaries,
    floats,
    integers,
    just,
    lists,
    none,
    recursive,
    register_type_strategy,
    sampled_from,
    sets,
    text,
    tuples,
)

from bowtie import _commands
from bowtie._cli import TEST_SUITE_DIALECT_URLS
from bowtie._report import Report, RunMetadata

# FIXME: probably via hypothesis-jsonschema
schemas = booleans() | dictionaries(
    keys=text(),
    values=recursive(
        none() | booleans() | floats() | text(printable),
        lambda children: lists(children)
        | dictionaries(text(printable), children),
    ),
)

seq = integers(min_value=1)
implementations = text(printable, min_size=1, max_size=50)
dialects = sampled_from(list(TEST_SUITE_DIALECT_URLS))


def tests(
    description=text(),
    instance=integers(),  # FIXME: probably via hypothesis-jsonschema
    valid=booleans() | none(),
    comment=text() | none(),
):
    r"""
    Generate `_commands.Test`\ s.
    """
    return builds(
        _commands.Test,
        description=description,
        instance=instance,
        valid=valid,
        comment=comment,
    )


def test_cases(
    description=text(),
    schema=schemas,
    tests=lists(tests(), min_size=1, max_size=8),
):
    r"""
    Generate `_commands.TestCase`\ s.
    """
    return builds(
        _commands.TestCase,
        description=description,
        schema=schema,
        tests=tests,
    )


successful_tests = sampled_from(
    [
        _commands.TestResult.VALID,
        _commands.TestResult.INVALID,
    ],
)
errored_tests = builds(
    _commands.ErroredTest,
    context=fixed_dictionaries(
        {},
        optional=dict(
            message=text(min_size=1),
            traceback=text(min_size=1),
            foo=text(),
        ),
    ),
)
skipped_tests = builds(
    _commands.SkippedTest,
    message=text(min_size=1) | none(),
    issue_url=text(min_size=1) | none(),
)
test_results = successful_tests | errored_tests | skipped_tests


@composite
def case_results(
    draw,
    implementations=implementations,
    seq=seq,
    test_results=test_results,
    expected=booleans() | none(),
    min_tests=1,
    max_tests=20,
):
    """
    A result for an individual test case.

    Note that the `Seq` for this result will be arbitrary, so don't use this to
    generate results in isolation without controlling for these IDs being what
    they need to be (i.e. report-wide unique).
    """
    size = draw(integers(min_value=min_tests, max_value=max_tests))
    # FIXME: only successful here
    return _commands.CaseResult(
        implementation=draw(implementations),
        seq=draw(seq),
        results=draw(lists(test_results, min_size=size, max_size=size)),
        expected=draw(lists(expected, min_size=size, max_size=size)),
    )


@composite
def cases_and_results(
    draw,
    implementations=sets(implementations, min_size=1, max_size=5),
    test_cases=test_cases(),
    min_cases=1,
    max_cases=8,
):
    """
    A set of test cases along with their results for generated implementations.
    """
    impls = draw(implementations)

    strategy = lists(
        tuples(seq, test_cases),
        min_size=min_cases,
        max_size=max_cases,
        unique_by=lambda each: each[0],
    )
    seq_cases = draw(strategy)

    return seq_cases, [
        draw(case_results(seq=just(seq), implementations=just(implementation)))
        for implementation in impls
        for (seq, _) in seq_cases
    ]


@composite
def report_data(
    draw,
    dialects=dialects,
    implementations=sets(implementations, min_size=1, max_size=8),
):
    """
    Generate Bowtie report data (suitable for `Report.from_input`).
    """
    dialect = draw(dialects)
    impls = draw(implementations)
    seq_cases, results = draw(cases_and_results(implementations=just(impls)))
    return [  # FIXME: Combine with the logic in CaseReporter
        RunMetadata(dialect=dialect, implementations=impls).serializable(),
        *[dict(case=case.serializable(), seq=seq) for seq, case in seq_cases],
        *[asdict(result) for result in results],
    ]


def reports(**kwargs):
    """
    Generate full Bowtie reports.
    """
    return builds(
        Report.from_input,
        input=report_data(**kwargs),
    )


# FIXME: These don't seem to do anything (in that builds() still fails?)
#        I also don't really understand why the builtin attrs support doesn't
#        autodetect more than it seems to be.
register_type_strategy(_commands.CaseResult, case_results())
register_type_strategy(_commands.Seq, seq)
register_type_strategy(_commands.Test, tests())
register_type_strategy(_commands.TestCase, test_cases())
register_type_strategy(_commands.TestResult, successful_tests)
register_type_strategy(_commands.SkippedTest, skipped_tests)
register_type_strategy(_commands.ErroredTest, errored_tests)
register_type_strategy(_commands.AnyTestResult, test_results)
register_type_strategy(Report, reports())