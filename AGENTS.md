Default to using uv instead of pip, virtualenv, poetry, or pyenv.

- Use `uv run <script.py>` instead of `python <script.py>` or `python3 <script.py>`
- Use `uv pip install` instead of `pip install` or `pip3 install`
- Use `uv add <package>` instead of `pip install <package>` in projects
- Use `uv init` instead of `poetry new` or manual `pyproject.toml` creation
- Use `uv sync` instead of `pip install -r requirements.txt` or `poetry install`
- Use `uv python install` instead of `pyenv install` or manual Python downloads
- Use `uv venv` instead of `python -m venv` or `virtualenv`
- Use `uv build` and `uv publish` instead of `python -m build` and `twine`

## Project Management

uv handles virtual environments automatically. Don't manually activate/deactivate.

Initialize projects:
```bash
uv init --app        # For applications
uv init --lib        # For libraries  
uv init --script     # For single scripts
```

Manage dependencies:
```bash
uv add requests              # Add dependency
uv add --dev pytest         # Add dev dependency
uv remove requests          # Remove dependency
uv sync                     # Sync environment with lockfile
uv lock                     # Update lockfile
```

## Python Management

uv manages Python installations. Don't use pyenv, conda, or system Python.

```bash
uv python install 3.12      # Install Python 3.12
uv python list              # List available Pythons
uv python pin 3.12          # Pin project to Python 3.12
```

## Running Code

Use `uv run` for all script execution:

```bash
uv run script.py                    # Run script with project deps
uv run -m pytest                     # Run module
uv run --with numpy script.py        # Run with additional package
uv run --isolated script.py          # Run in isolated environment
```

## Scripts & Tools

Install and run tools without polluting global environment:

```bash
uv tool install ruff               # Install tool globally
uv tool run --from ruff ruff check # Run without installing
```

For inline script dependencies:
```python
# /// script
# dependencies = ["requests", "pandas"]
# ///

import requests
import pandas as pd
# script code here
```

Then: `uv run script.py` automatically installs dependencies.

## Environment Variables

uv automatically loads `.env` files with `uv run --env-file .env` or by default in projects.

## Performance

- uv is 10-100x faster than pip
- Parallel downloads and installations
- Global cache prevents re-downloads
- Use `--compile-bytecode` for faster imports

For more information, see https://docs.astral.sh/uv/

# Writing Commit Messages

Follow this protocol when preparing to commit code changes.
1. Identify changes: Run `git status`.
2. Validate changes: Apply appropriate syntax checks (e.g., `uv run -m py_compile [file]`, `bash -n [file]`) and run relevant tests (e.g., `uv run pytest`) for all modified files. If validation fails, fix the issues.
3. Review staged changes: Run `git diff --cached`.
4. Create commit message: Follow Conventional Commits pattern ("type(scope): description"). Detail complex changes in the commit body.
5. Verify commit: Run `git log -1 --stat`.

# Analyzing Code and Identifying Patterns

Start by inventorying the codebase using `rg --files` to list all files, filtering by directory or extension as needed. Search for structural patterns, anti-patterns, and repetitive code blocks using precise `rg` queries. Focus on high-impact areas such as core logic, shared utilities, and frequently modified files.

Cross-reference findings with version control history to assess context. Use `git blame` on critical files to identify ownership, change frequency, and potential technical debt hotspots. Check test coverage for impacted components by searching for corresponding test files or test functions.

Use insights for actionable recommendations. Prioritize based on impact, linking each suggestion to specific files, functions, or lines. For example:
- Replace duplicated logic in `utils/data_processing.py` (lines 15-30) with a shared helper function.
- Standardize error handling in `api/endpoints/` by adopting the pattern used in `api/users.py`.
- Break down monolithic functions exceeding 50 lines, starting with `services/report_generator.py:process_data()`.

Document patterns and recommendations in an ADR `.md` file in a `docs/` folder, ensuring traceability to the original code locations. Use these insights to guide refactoring, inform new feature design, and improve maintainability. Validate proposals by verifying consistency with existing conventions and testing strategies.

## Iterators

I'll start by looking at a Python language feature that's an important foundation for writing functional-style programs: iterators.

An iterator is an object representing a stream of data; this object returns the data one element at a time. A Python iterator must support a method called `~iterator.__next__` that takes no arguments and always returns the next element of the stream. If there are no more elements in the stream, `~iterator.__next__` must raise the `StopIteration` exception. Iterators don't have to be finite, though; it's perfectly reasonable to write an iterator that produces an infinite stream of data.

The built-in `iter` function takes an arbitrary object and tries to return an iterator that will return the object's contents or elements, raising `TypeError` if the object doesn't support iteration. Several of Python's built-in data types support iteration, the most common being lists and dictionaries. An object is called `iterable` if you can get an iterator for it.

You can experiment with the iteration interface manually:

> \>\>\> L = \[1, 2, 3\] \>\>\> it = iter(L) \>\>\> it \#doctest: +ELLIPSIS \<...iterator object at ...\> \>\>\> it.\_\_next\_\_() \# same as next(it) 1 \>\>\> next(it) 2 \>\>\> next(it) 3 \>\>\> next(it) Traceback (most recent call last): File "\<stdin\>", line 1, in \<module\> StopIteration \>\>\>

Python expects iterable objects in several different contexts, the most important being the `for` statement. In the statement `for X in Y`, Y must be an iterator or some object for which `iter` can create an iterator. These two statements are equivalent:

    for i in iter(obj):
        print(i)

    for i in obj:
        print(i)

Iterators can be materialized as lists or tuples by using the `list` or `tuple` constructor functions:

> \>\>\> L = \[1, 2, 3\] \>\>\> iterator = iter(L) \>\>\> t = tuple(iterator) \>\>\> t (1, 2, 3)

Sequence unpacking also supports iterators: if you know an iterator will return N elements, you can unpack them into an N-tuple:

> \>\>\> L = \[1, 2, 3\] \>\>\> iterator = iter(L) \>\>\> a, b, c = iterator \>\>\> a, b, c (1, 2, 3)

Built-in functions such as `max` and `min` can take a single iterator argument and will return the largest or smallest element. The `"in"` and `"not in"` operators also support iterators: `X in iterator` is true if X is found in the stream returned by the iterator. You'll run into obvious problems if the iterator is infinite; `max`, `min` will never return, and if the element X never appears in the stream, the `"in"` and `"not in"` operators won't return either.

Note that you can only go forward in an iterator; there's no way to get the previous element, reset the iterator, or make a copy of it. Iterator objects can optionally provide these additional capabilities, but the iterator protocol only specifies the `~iterator.__next__` method. Functions may therefore consume all of the iterator's output, and if you need to do something different with the same stream, you'll have to create a new iterator.

### Data Types That Support Iterators

We've already seen how lists and tuples support iterators. In fact, any Python sequence type, such as strings, will automatically support creation of an iterator.

Calling `iter` on a dictionary returns an iterator that will loop over the dictionary's keys:

    >>> m = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    ...      'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    >>> for key in m:
    ...     print(key, m[key])
    Jan 1
    Feb 2
    Mar 3
    Apr 4
    May 5
    Jun 6
    Jul 7
    Aug 8
    Sep 9
    Oct 10
    Nov 11
    Dec 12

Note that starting with Python 3.7, dictionary iteration order is guaranteed to be the same as the insertion order. In earlier versions, the behaviour was unspecified and could vary between implementations.

Applying `iter` to a dictionary always loops over the keys, but dictionaries have methods that return other iterators. If you want to iterate over values or key/value pairs, you can explicitly call the `~dict.values` or `~dict.items` methods to get an appropriate iterator.

The `dict` constructor can accept an iterator that returns a finite stream of `(key, value)` tuples:

> \>\>\> L = \[('Italy', 'Rome'), ('France', 'Paris'), ('US', 'Washington DC')\] \>\>\> dict(iter(L)) {'Italy': 'Rome', 'France': 'Paris', 'US': 'Washington DC'}

Files also support iteration by calling the `~io.TextIOBase.readline` method until there are no more lines in the file. This means you can read each line of a file like this:

    for line in file:
        # do something for each line
        ...

Sets can take their contents from an iterable and let you iterate over the set's elements:

    >>> S = {2, 3, 5, 7, 11, 13}
    >>> for i in S:
    ...     print(i)
    2
    3
    5
    7
    11
    13

## Generator expressions and list comprehensions

Two common operations on an iterator's output are 1) performing some operation for every element, 2) selecting a subset of elements that meet some condition. For example, given a list of strings, you might want to strip off trailing whitespace from each line or extract all the strings containing a given substring.

List comprehensions and generator expressions (short form: "listcomps" and "genexps") are a concise notation for such operations, borrowed from the functional programming language Haskell (<https://www.haskell.org/>). You can strip all the whitespace from a stream of strings with the following code:

    >>> line_list = ['  line 1\n', 'line 2  \n', ' \n', '']

    >>> # Generator expression -- returns iterator
    >>> stripped_iter = (line.strip() for line in line_list)

    >>> # List comprehension -- returns list
    >>> stripped_list = [line.strip() for line in line_list]

You can select only certain elements by adding an `"if"` condition:

    >>> stripped_list = [line.strip() for line in line_list
    ...                  if line != ""]

With a list comprehension, you get back a Python list; `stripped_list` is a list containing the resulting lines, not an iterator. Generator expressions return an iterator that computes the values as necessary, not needing to materialize all the values at once. This means that list comprehensions aren't useful if you're working with iterators that return an infinite stream or a very large amount of data. Generator expressions are preferable in these situations.

Generator expressions are surrounded by parentheses ("()") and list comprehensions are surrounded by square brackets ("\[\]"). Generator expressions have the form:

    ( expression for expr in sequence1
                 if condition1
                 for expr2 in sequence2
                 if condition2
                 for expr3 in sequence3
                 if condition3
                 ...
                 for exprN in sequenceN
                 if conditionN )

Again, for a list comprehension only the outside brackets are different (square brackets instead of parentheses).

The elements of the generated output will be the successive values of `expression`. The `if` clauses are all optional; if present, `expression` is only evaluated and added to the result when `condition` is true.

Generator expressions always have to be written inside parentheses, but the parentheses signalling a function call also count. If you want to create an iterator that will be immediately passed to a function you can write:

    obj_total = sum(obj.count for obj in list_all_objects())

The `for...in` clauses contain the sequences to be iterated over. The sequences do not have to be the same length, because they are iterated over from left to right, **not** in parallel. For each element in `sequence1`, `sequence2` is looped over from the beginning. `sequence3` is then looped over for each resulting pair of elements from `sequence1` and `sequence2`.

To put it another way, a list comprehension or generator expression is equivalent to the following Python code:

    for expr1 in sequence1:
        if not (condition1):
            continue   # Skip this element
        for expr2 in sequence2:
            if not (condition2):
                continue   # Skip this element
            ...
            for exprN in sequenceN:
                if not (conditionN):
                    continue   # Skip this element

                # Output the value of
                # the expression.

This means that when there are multiple `for...in` clauses but no `if` clauses, the length of the resulting output will be equal to the product of the lengths of all the sequences. If you have two lists of length 3, the output list is 9 elements long:

> \>\>\> seq1 = 'abc' \>\>\> seq2 = (1, 2, 3) \>\>\> \[(x, y) for x in seq1 for y in seq2\] \#doctest: +NORMALIZE_WHITESPACE \[('a', 1), ('a', 2), ('a', 3), ('b', 1), ('b', 2), ('b', 3), ('c', 1), ('c', 2), ('c', 3)\]

To avoid introducing an ambiguity into Python's grammar, if `expression` is creating a tuple, it must be surrounded with parentheses. The first list comprehension below is a syntax error, while the second one is correct:

    # Syntax error
    [x, y for x in seq1 for y in seq2]
    # Correct
    [(x, y) for x in seq1 for y in seq2]

## Generators

Generators are a special class of functions that simplify the task of writing iterators. Regular functions compute a value and return it, but generators return an iterator that returns a stream of values.

You're doubtless familiar with how regular function calls work in Python or C. When you call a function, it gets a private namespace where its local variables are created. When the function reaches a `return` statement, the local variables are destroyed and the value is returned to the caller. A later call to the same function creates a new private namespace and a fresh set of local variables. But, what if the local variables weren't thrown away on exiting a function? What if you could later resume the function where it left off? This is what generators provide; they can be thought of as resumable functions.

Here's the simplest example of a generator function:

> \>\>\> def generate_ints(N): ... for i in range(N): ... yield i

Any function containing a `yield` keyword is a generator function; this is detected by Python's `bytecode` compiler which compiles the function specially as a result.

When you call a generator function, it doesn't return a single value; instead it returns a generator object that supports the iterator protocol. On executing the `yield` expression, the generator outputs the value of `i`, similar to a `return` statement. The big difference between `yield` and a `return` statement is that on reaching a `yield` the generator's state of execution is suspended and local variables are preserved. On the next call to the generator's `~generator.__next__` method, the function will resume executing.

Here's a sample usage of the `generate_ints()` generator:

> \>\>\> gen = generate_ints(3) \>\>\> gen \#doctest: +ELLIPSIS \<generator object generate_ints at ...\> \>\>\> next(gen) 0 \>\>\> next(gen) 1 \>\>\> next(gen) 2 \>\>\> next(gen) Traceback (most recent call last): File "stdin", line 1, in \<module\> File "stdin", line 2, in generate_ints StopIteration

You could equally write `for i in generate_ints(5)`, or `a, b, c = generate_ints(3)`.

Inside a generator function, `return value` causes `StopIteration(value)` to be raised from the `~generator.__next__` method. Once this happens, or the bottom of the function is reached, the procession of values ends and the generator cannot yield any further values.

You could achieve the effect of generators manually by writing your own class and storing all the local variables of the generator as instance variables. For example, returning a list of integers could be done by setting `self.count` to 0, and having the `~iterator.__next__` method increment `self.count` and return it. However, for a moderately complicated generator, writing a corresponding class can be much messier.

The test suite included with Python's library, `Lib/test/test_generators.py`, contains a number of more interesting examples. Here's one generator that implements an in-order traversal of a tree using generators recursively. :

    # A recursive generator that generates Tree leaves in in-order.
    def inorder(t):
        if t:
            for x in inorder(t.left):
                yield x

            yield t.label

            for x in inorder(t.right):
                yield x

Two other examples in `test_generators.py` produce solutions for the N-Queens problem (placing N queens on an NxN chess board so that no queen threatens another) and the Knight's Tour (finding a route that takes a knight to every square of an NxN chessboard without visiting any square twice).

### Passing values into a generator

In Python 2.4 and earlier, generators only produced output. Once a generator's code was invoked to create an iterator, there was no way to pass any new information into the function when its execution is resumed. You could hack together this ability by making the generator look at a global variable or by passing in some mutable object that callers then modify, but these approaches are messy.

In Python 2.5 there's a simple way to pass values into a generator. `yield` became an expression, returning a value that can be assigned to a variable or otherwise operated on:

    val = (yield i)

I recommend that you **always** put parentheses around a `yield` expression when you're doing something with the returned value, as in the above example. The parentheses aren't always necessary, but it's easier to always add them instead of having to remember when they're needed.

(`342` explains the exact rules, which are that a `yield`-expression must always be parenthesized except when it occurs at the top-level expression on the right-hand side of an assignment. This means you can write `val = yield i` but have to use parentheses when there's an operation, as in `val = (yield i) + 12`.)

Values are sent into a generator by calling its `send(value)
<generator.send>` method. This method resumes the generator's code and the `yield` expression returns the specified value. If the regular `~generator.__next__` method is called, the `yield` returns `None`.

Here's a simple counter that increments by 1 and allows changing the value of the internal counter.

<div class="testcode">

def counter(maximum):  
i = 0 while i \< maximum: val = (yield i) \# If value provided, change counter if val is not None: i = val else: i += 1

</div>

And here's an example of changing the counter:

> \>\>\> it = counter(10) \#doctest: +SKIP \>\>\> next(it) \#doctest: +SKIP 0 \>\>\> next(it) \#doctest: +SKIP 1 \>\>\> it.send(8) \#doctest: +SKIP 8 \>\>\> next(it) \#doctest: +SKIP 9 \>\>\> next(it) \#doctest: +SKIP Traceback (most recent call last): File "t.py", line 15, in \<module\> it.next() StopIteration

Because `yield` will often be returning `None`, you should always check for this case. Don't just use its value in expressions unless you're sure that the `~generator.send` method will be the only method used to resume your generator function.

In addition to `~generator.send`, there are two other methods on generators:

- `throw(value) <generator.throw>` is used to raise an exception inside the generator; the exception is raised by the `yield` expression where the generator's execution is paused.

- `~generator.close` sends a `GeneratorExit` exception to the generator to terminate the iteration. On receiving this exception, the generator's code must either raise `GeneratorExit` or `StopIteration`; catching the exception and doing anything else is illegal and will trigger a `RuntimeError`. `~generator.close` will also be called by Python's garbage collector when the generator is garbage-collected.

  If you need to run cleanup code when a `GeneratorExit` occurs, I suggest using a `try: ... finally:` suite instead of catching `GeneratorExit`.

The cumulative effect of these changes is to turn generators from one-way producers of information into both producers and consumers.

Generators also become **coroutines**, a more generalized form of subroutines. Subroutines are entered at one point and exited at another point (the top of the function, and a `return` statement), but coroutines can be entered, exited, and resumed at many different points (the `yield` statements).

## Built-in functions

Let's look in more detail at built-in functions often used with iterators.

Two of Python's built-in functions, `map` and `filter` duplicate the features of generator expressions:

`map(f, iterA, iterB, ...) <map>` returns an iterator over the sequence  
`f(iterA[0], iterB[0]), f(iterA[1], iterB[1]), f(iterA[2], iterB[2]), ...`.

> \>\>\> def upper(s): ... return s.upper()
>
> \>\>\> list(map(upper, \['sentence', 'fragment'\])) \['SENTENCE', 'FRAGMENT'\] \>\>\> \[upper(s) for s in \['sentence', 'fragment'\]\] \['SENTENCE', 'FRAGMENT'\]

You can of course achieve the same effect with a list comprehension.

`filter(predicate, iter) <filter>` returns an iterator over all the sequence elements that meet a certain condition, and is similarly duplicated by list comprehensions. A **predicate** is a function that returns the truth value of some condition; for use with `filter`, the predicate must take a single value.

> \>\>\> def is_even(x): ... return (x % 2) == 0
>
> \>\>\> list(filter(is_even, range(10))) \[0, 2, 4, 6, 8\]

This can also be written as a list comprehension:

> \>\>\> list(x for x in range(10) if is_even(x)) \[0, 2, 4, 6, 8\]

`enumerate(iter, start=0) <enumerate>` counts off the elements in the iterable returning 2-tuples containing the count (from *start*) and each element. :

    >>> for item in enumerate(['subject', 'verb', 'object']):
    ...     print(item)
    (0, 'subject')
    (1, 'verb')
    (2, 'object')

`enumerate` is often used when looping through a list and recording the indexes at which certain conditions are met:

    f = open('data.txt', 'r')
    for i, line in enumerate(f):
        if line.strip() == '':
            print('Blank line at line #%i' % i)

`sorted(iterable, key=None, reverse=False) <sorted>` collects all the elements of the iterable into a list, sorts the list, and returns the sorted result. The *key* and *reverse* arguments are passed through to the constructed list's `~list.sort` method. :

    >>> import random
    >>> # Generate 8 random numbers between [0, 10000)
    >>> rand_list = random.sample(range(10000), 8)
    >>> rand_list  #doctest: +SKIP
    [769, 7953, 9828, 6431, 8442, 9878, 6213, 2207]
    >>> sorted(rand_list)  #doctest: +SKIP
    [769, 2207, 6213, 6431, 7953, 8442, 9828, 9878]
    >>> sorted(rand_list, reverse=True)  #doctest: +SKIP
    [9878, 9828, 8442, 7953, 6431, 6213, 2207, 769]

(For a more detailed discussion of sorting, see the `sortinghowto`.)

The `any(iter) <any>` and `all(iter) <all>` built-ins look at the truth values of an iterable's contents. `any` returns `True` if any element in the iterable is a true value, and `all` returns `True` if all of the elements are true values:

> \>\>\> any(\[0, 1, 0\]) True \>\>\> any(\[0, 0, 0\]) False \>\>\> any(\[1, 1, 1\]) True \>\>\> all(\[0, 1, 0\]) False \>\>\> all(\[0, 0, 0\]) False \>\>\> all(\[1, 1, 1\]) True

`zip(iterA, iterB, ...) <zip>` takes one element from each iterable and returns them in a tuple:

    zip(['a', 'b', 'c'], (1, 2, 3)) =>
      ('a', 1), ('b', 2), ('c', 3)

It doesn't construct an in-memory list and exhaust all the input iterators before returning; instead tuples are constructed and returned only if they're requested. (The technical term for this behaviour is [lazy evaluation](https://en.wikipedia.org/wiki/Lazy_evaluation).)

This iterator is intended to be used with iterables that are all of the same length. If the iterables are of different lengths, the resulting stream will be the same length as the shortest iterable. :

    zip(['a', 'b'], (1, 2, 3)) =>
      ('a', 1), ('b', 2)

You should avoid doing this, though, because an element may be taken from the longer iterators and discarded. This means you can't go on to use the iterators further because you risk skipping a discarded element.

## The itertools module

The `itertools` module contains a number of commonly used iterators as well as functions for combining several iterators. This section will introduce the module's contents by showing small examples.

The module's functions fall into a few broad classes:

- Functions that create a new iterator based on an existing iterator.
- Functions for treating an iterator's elements as function arguments.
- Functions for selecting portions of an iterator's output.
- A function for grouping an iterator's output.

### Creating new iterators

`itertools.count(start, step) <itertools.count>` returns an infinite stream of evenly spaced values. You can optionally supply the starting number, which defaults to 0, and the interval between numbers, which defaults to 1:

    itertools.count() =>
      0, 1, 2, 3, 4, 5, 6, 7, 8, 9, ...
    itertools.count(10) =>
      10, 11, 12, 13, 14, 15, 16, 17, 18, 19, ...
    itertools.count(10, 5) =>
      10, 15, 20, 25, 30, 35, 40, 45, 50, 55, ...

`itertools.cycle(iter) <itertools.cycle>` saves a copy of the contents of a provided iterable and returns a new iterator that returns its elements from first to last. The new iterator will repeat these elements infinitely. :

    itertools.cycle([1, 2, 3, 4, 5]) =>
      1, 2, 3, 4, 5, 1, 2, 3, 4, 5, ...

`itertools.repeat(elem, [n]) <itertools.repeat>` returns the provided element *n* times, or returns the element endlessly if *n* is not provided. :

    itertools.repeat('abc') =>
      abc, abc, abc, abc, abc, abc, abc, abc, abc, abc, ...
    itertools.repeat('abc', 5) =>
      abc, abc, abc, abc, abc

`itertools.chain(iterA, iterB, ...) <itertools.chain>` takes an arbitrary number of iterables as input, and returns all the elements of the first iterator, then all the elements of the second, and so on, until all of the iterables have been exhausted. :

    itertools.chain(['a', 'b', 'c'], (1, 2, 3)) =>
      a, b, c, 1, 2, 3

`itertools.islice(iter, [start], stop, [step]) <itertools.islice>` returns a stream that's a slice of the iterator. With a single *stop* argument, it will return the first *stop* elements. If you supply a starting index, you'll get *stop-start* elements, and if you supply a value for *step*, elements will be skipped accordingly. Unlike Python's string and list slicing, you can't use negative values for *start*, *stop*, or *step*. :

    itertools.islice(range(10), 8) =>
      0, 1, 2, 3, 4, 5, 6, 7
    itertools.islice(range(10), 2, 8) =>
      2, 3, 4, 5, 6, 7
    itertools.islice(range(10), 2, 8, 2) =>
      2, 4, 6

`itertools.tee(iter, [n]) <itertools.tee>` replicates an iterator; it returns *n* independent iterators that will all return the contents of the source iterator. If you don't supply a value for *n*, the default is 2. Replicating iterators requires saving some of the contents of the source iterator, so this can consume significant memory if the iterator is large and one of the new iterators is consumed more than the others. :

    itertools.tee( itertools.count() ) =>
       iterA, iterB

    where iterA ->
       0, 1, 2, 3, 4, 5, 6, 7, 8, 9, ...

    and   iterB ->
       0, 1, 2, 3, 4, 5, 6, 7, 8, 9, ...

### Calling functions on elements

The `operator` module contains a set of functions corresponding to Python's operators. Some examples are `operator.add(a, b) <operator.add>` (adds two values), `operator.ne(a, b)  <operator.ne>` (same as `a != b`), and `operator.attrgetter('id') <operator.attrgetter>` (returns a callable that fetches the `.id` attribute).

`itertools.starmap(func, iter) <itertools.starmap>` assumes that the iterable will return a stream of tuples, and calls *func* using these tuples as the arguments:

    itertools.starmap(os.path.join,
                      [('/bin', 'python'), ('/usr', 'bin', 'java'),
                       ('/usr', 'bin', 'perl'), ('/usr', 'bin', 'ruby')])
    =>
      /bin/python, /usr/bin/java, /usr/bin/perl, /usr/bin/ruby

### Selecting elements

Another group of functions chooses a subset of an iterator's elements based on a predicate.

`itertools.filterfalse(predicate, iter) <itertools.filterfalse>` is the opposite of `filter`, returning all elements for which the predicate returns false:

    itertools.filterfalse(is_even, itertools.count()) =>
      1, 3, 5, 7, 9, 11, 13, 15, ...

`itertools.takewhile(predicate, iter) <itertools.takewhile>` returns elements for as long as the predicate returns true. Once the predicate returns false, the iterator will signal the end of its results. :

    def less_than_10(x):
        return x < 10

    itertools.takewhile(less_than_10, itertools.count()) =>
      0, 1, 2, 3, 4, 5, 6, 7, 8, 9

    itertools.takewhile(is_even, itertools.count()) =>
      0

`itertools.dropwhile(predicate, iter) <itertools.dropwhile>` discards elements while the predicate returns true, and then returns the rest of the iterable's results. :

    itertools.dropwhile(less_than_10, itertools.count()) =>
      10, 11, 12, 13, 14, 15, 16, 17, 18, 19, ...

    itertools.dropwhile(is_even, itertools.count()) =>
      1, 2, 3, 4, 5, 6, 7, 8, 9, 10, ...

`itertools.compress(data, selectors) <itertools.compress>` takes two iterators and returns only those elements of *data* for which the corresponding element of *selectors* is true, stopping whenever either one is exhausted:

    itertools.compress([1, 2, 3, 4, 5], [True, True, False, False, True]) =>
       1, 2, 5

### Combinatoric functions

The `itertools.combinations(iterable, r) <itertools.combinations>` returns an iterator giving all possible *r*-tuple combinations of the elements contained in *iterable*. :

    itertools.combinations([1, 2, 3, 4, 5], 2) =>
      (1, 2), (1, 3), (1, 4), (1, 5),
      (2, 3), (2, 4), (2, 5),
      (3, 4), (3, 5),
      (4, 5)

    itertools.combinations([1, 2, 3, 4, 5], 3) =>
      (1, 2, 3), (1, 2, 4), (1, 2, 5), (1, 3, 4), (1, 3, 5), (1, 4, 5),
      (2, 3, 4), (2, 3, 5), (2, 4, 5),
      (3, 4, 5)

The elements within each tuple remain in the same order as *iterable* returned them. For example, the number 1 is always before 2, 3, 4, or 5 in the examples above. A similar function, `itertools.permutations(iterable, r=None) <itertools.permutations>`, removes this constraint on the order, returning all possible arrangements of length *r*:

    itertools.permutations([1, 2, 3, 4, 5], 2) =>
      (1, 2), (1, 3), (1, 4), (1, 5),
      (2, 1), (2, 3), (2, 4), (2, 5),
      (3, 1), (3, 2), (3, 4), (3, 5),
      (4, 1), (4, 2), (4, 3), (4, 5),
      (5, 1), (5, 2), (5, 3), (5, 4)

    itertools.permutations([1, 2, 3, 4, 5]) =>
      (1, 2, 3, 4, 5), (1, 2, 3, 5, 4), (1, 2, 4, 3, 5),
      ...
      (5, 4, 3, 2, 1)

If you don't supply a value for *r* the length of the iterable is used, meaning that all the elements are permuted.

Note that these functions produce all of the possible combinations by position and don't require that the contents of *iterable* are unique:

    itertools.permutations('aba', 3) =>
      ('a', 'b', 'a'), ('a', 'a', 'b'), ('b', 'a', 'a'),
      ('b', 'a', 'a'), ('a', 'a', 'b'), ('a', 'b', 'a')

The identical tuple `('a', 'a', 'b')` occurs twice, but the two 'a' strings came from different positions.

The `itertools.combinations_with_replacement(iterable, r) <itertools.combinations_with_replacement>` function relaxes a different constraint: elements can be repeated within a single tuple. Conceptually an element is selected for the first position of each tuple and then is replaced before the second element is selected. :

    itertools.combinations_with_replacement([1, 2, 3, 4, 5], 2) =>
      (1, 1), (1, 2), (1, 3), (1, 4), (1, 5),
      (2, 2), (2, 3), (2, 4), (2, 5),
      (3, 3), (3, 4), (3, 5),
      (4, 4), (4, 5),
      (5, 5)

### Grouping elements

The last function I'll discuss, `itertools.groupby(iter, key_func=None)
<itertools.groupby>`, is the most complicated. `key_func(elem)` is a function that can compute a key value for each element returned by the iterable. If you don't supply a key function, the key is simply each element itself.

`~itertools.groupby` collects all the consecutive elements from the underlying iterable that have the same key value, and returns a stream of 2-tuples containing a key value and an iterator for the elements with that key.

    city_list = [('Decatur', 'AL'), ('Huntsville', 'AL'), ('Selma', 'AL'),
                 ('Anchorage', 'AK'), ('Nome', 'AK'),
                 ('Flagstaff', 'AZ'), ('Phoenix', 'AZ'), ('Tucson', 'AZ'),
                 ...
                ]

    def get_state(city_state):
        return city_state[1]

    itertools.groupby(city_list, get_state) =>
      ('AL', iterator-1),
      ('AK', iterator-2),
      ('AZ', iterator-3), ...

    where
    iterator-1 =>
      ('Decatur', 'AL'), ('Huntsville', 'AL'), ('Selma', 'AL')
    iterator-2 =>
      ('Anchorage', 'AK'), ('Nome', 'AK')
    iterator-3 =>
      ('Flagstaff', 'AZ'), ('Phoenix', 'AZ'), ('Tucson', 'AZ')

`~itertools.groupby` assumes that the underlying iterable's contents will already be sorted based on the key. Note that the returned iterators also use the underlying iterable, so you have to consume the results of iterator-1 before requesting iterator-2 and its corresponding key.

## The functools module

The `functools` module contains some higher-order functions. A **higher-order function** takes one or more functions as input and returns a new function. The most useful tool in this module is the `functools.partial` function.

For programs written in a functional style, you'll sometimes want to construct variants of existing functions that have some of the parameters filled in. Consider a Python function `f(a, b, c)`; you may wish to create a new function `g(b, c)` that's equivalent to `f(1, b, c)`; you're filling in a value for one of `f()`'s parameters. This is called "partial function application".

The constructor for `~functools.partial` takes the arguments `(function, arg1, arg2, ..., kwarg1=value1, kwarg2=value2)`. The resulting object is callable, so you can just call it to invoke `function` with the filled-in arguments.

Here's a small but realistic example:

    import functools

    def log(message, subsystem):
        """Write the contents of 'message' to the specified subsystem."""
        print('%s: %s' % (subsystem, message))
        ...

    server_log = functools.partial(log, subsystem='server')
    server_log('Unable to open socket')

`functools.reduce(func, iter, [initial_value]) <functools.reduce>` cumulatively performs an operation on all the iterable's elements and, therefore, can't be applied to infinite iterables. *func* must be a function that takes two elements and returns a single value. `functools.reduce` takes the first two elements A and B returned by the iterator and calculates `func(A, B)`. It then requests the third element, C, calculates `func(func(A, B), C)`, combines this result with the fourth element returned, and continues until the iterable is exhausted. If the iterable returns no values at all, a `TypeError` exception is raised. If the initial value is supplied, it's used as a starting point and `func(initial_value, A)` is the first calculation. :

    >>> import operator, functools
    >>> functools.reduce(operator.concat, ['A', 'BB', 'C'])
    'ABBC'
    >>> functools.reduce(operator.concat, [])
    Traceback (most recent call last):
      ...
    TypeError: reduce() of empty sequence with no initial value
    >>> functools.reduce(operator.mul, [1, 2, 3], 1)
    6
    >>> functools.reduce(operator.mul, [], 1)
    1

If you use `operator.add` with `functools.reduce`, you'll add up all the elements of the iterable. This case is so common that there's a special built-in called `sum` to compute it:

> \>\>\> import functools, operator \>\>\> functools.reduce(operator.add, \[1, 2, 3, 4\], 0) 10 \>\>\> sum(\[1, 2, 3, 4\]) 10 \>\>\> sum(\[\]) 0

For many uses of `functools.reduce`, though, it can be clearer to just write the obvious `for` loop:

    import functools
    # Instead of:
    product = functools.reduce(operator.mul, [1, 2, 3], 1)

    # You can write:
    product = 1
    for i in [1, 2, 3]:
        product *= i

A related function is `itertools.accumulate(iterable, func=operator.add)
<itertools.accumulate>`. It performs the same calculation, but instead of returning only the final result, `~itertools.accumulate` returns an iterator that also yields each partial result:

    itertools.accumulate([1, 2, 3, 4, 5]) =>
      1, 3, 6, 10, 15

    itertools.accumulate([1, 2, 3, 4, 5], operator.mul) =>
      1, 2, 6, 24, 120

### The operator module

The `operator` module was mentioned earlier. It contains a set of functions corresponding to Python's operators. These functions are often useful in functional-style code because they save you from writing trivial functions that perform a single operation.

Some of the functions in this module are:

- Math operations: `add()`, `sub()`, `mul()`, `floordiv()`, `abs()`, ...
- Logical operations: `not_()`, `truth()`.
- Bitwise operations: `and_()`, `or_()`, `invert()`.
- Comparisons: `eq()`, `ne()`, `lt()`, `le()`, `gt()`, and `ge()`.
- Object identity: `is_()`, `is_not()`.

Consult the operator module's documentation for a complete list.

## Small functions and the lambda expression

When writing functional-style programs, you'll often need little functions that act as predicates or that combine elements in some way.

If there's a Python built-in or a module function that's suitable, you don't need to define a new function at all:

    stripped_lines = [line.strip() for line in lines]
    existing_files = filter(os.path.exists, file_list)

If the function you need doesn't exist, you need to write it. One way to write small functions is to use the `lambda` expression. `lambda` takes a number of parameters and an expression combining these parameters, and creates an anonymous function that returns the value of the expression:

    adder = lambda x, y: x+y

    print_assign = lambda name, value: name + '=' + str(value)

An alternative is to just use the `def` statement and define a function in the usual way:

    def adder(x, y):
        return x + y

    def print_assign(name, value):
        return name + '=' + str(value)

Which alternative is preferable? That's a style question; my usual course is to avoid using `lambda`.

One reason for my preference is that `lambda` is quite limited in the functions it can define. The result has to be computable as a single expression, which means you can't have multiway `if... elif... else` comparisons or `try... except` statements. If you try to do too much in a `lambda` statement, you'll end up with an overly complicated expression that's hard to read. Quick, what's the following code doing? :

    import functools
    total = functools.reduce(lambda a, b: (0, a[1] + b[1]), items)[1]

You can figure it out, but it takes time to disentangle the expression to figure out what's going on. Using a short nested `def` statements makes things a little bit better:

    import functools
    def combine(a, b):
        return 0, a[1] + b[1]

    total = functools.reduce(combine, items)[1]

But it would be best of all if I had simply used a `for` loop:

    total = 0
    for a, b in items:
        total += b

Or the `sum` built-in and a generator expression:

    total = sum(b for a, b in items)

Many uses of `functools.reduce` are clearer when written as `for` loops.

Fredrik Lundh once suggested the following set of rules for refactoring uses of `lambda`:

1.  Write a lambda function.
2.  Write a comment explaining what the heck that lambda does.
3.  Study the comment for a while, and think of a name that captures the essence of the comment.
4.  Convert the lambda to a def statement, using that name.
5.  Remove the comment.

I really like these rules, but you're free to disagree about whether this lambda-free style is better.

# LibCST

Always use LibCST to parse Python source code. Always parse Python source code as a CST tree, and never as an AST.

Never use other parsing libraries, such as AST, astor, astroid, or any other library.

LibCST keeps all formatting details (comments, whitespaces, parentheses, etc).

LibCST creates a compromise between an Abstract Syntax Tree (AST) and a traditional Concrete Syntax Tree (CST). By carefully reorganizing and naming node types and fields, we've created a lossless CST that looks and feels like an AST.

While there are plenty of ways to interact with LibCST, we recommend some patterns over others. Various best practices are laid out here along with their justifications.

## Avoid `isinstance` when traversing

Excessive use of `isinstance` implies that you should rewrite your check as a matcher or unroll it into a set of visitor methods. Often, you should make use of `~libcst.ensure_type` to make your type checker aware of a node's type.

Often it is far easier to use `libcst-matchers` over explicit instance checks in a transform. Matching against some pattern and then extracting a value from a node's child is often easier and far more readable. Unfortunately this clashes with various type-checkers which do not understand that `~libcst.matchers.matches` guarantees a particular set of children. Instead of instance checks, you should use `~libcst.ensure_type` which can be inlined and nested.

For example, if you have written the following:

    def get_identifier_name(node: cst.CSTNode) -> Optional[str]:
        if m.matches(node, m.Name()):
            assert isinstance(node, cst.Name)
            return node.value
        return None

You could instead write something like:

    def get_identifier_name(node: cst.CSTNode) -> Optional[str]:
        return (
            cst.ensure_type(node, cst.Name).value
            if m.matches(node, m.Name())
            else None
        )

If you find yourself attempting to manually traverse a tree using `isinstance`, you can often rewrite your code using visitor methods instead. Nested instance checks can often be unrolled into visitors methods along with matcher decorators. This may entail adding additional state to your visitor, but the resulting code is far more likely to work after changes to LibCST itself. For example, if you have written the following:

    class CountBazFoobarArgs(cst.CSTVisitor):
        """
        Given a set of function names, count how many arguments to those function
        calls are the identifiers "baz" or "foobar".
        """

        def __init__(self, functions: Set[str]) -> None:
            super().__init__()
            self.functions: Set[str] = functions
            self.arg_count: int = 0

        def visit_Call(self, node: cst.Call) -> None:
            # See if the call itself is one of our functions we care about
            if isinstance(node.func, cst.Name) and node.func.value in self.functions:
                # Loop through each argument
                for arg in node.args:
                    # See if the argument is an identifier matching what we want to count
                    if isinstance(arg.value, cst.Name) and arg.value.value in {"baz", "foobar"}:
                        self.arg_count += 1

You could instead write something like:

    class CountBazFoobarArgs(m.MatcherDecoratableVisitor):
        """
        Given a set of function names, count how many arguments to those function
        calls are the identifiers "baz" or "foobar".
        """

        def __init__(self, functions: Set[str]) -> None:
            super().__init__()
            self.functions: Set[str] = functions
            self.arg_count: int = 0
            self.call_stack: List[str] = []

        def visit_Call(self, node: cst.Call) -> None:
            # Store all calls in a stack
            if m.matches(node.func, m.Name()):
                self.call_stack.append(cst.ensure_type(node.func, cst.Name).value)

        def leave_Call(self, original_node: cst.Call) -> None:
            # Pop the latest call off the stack
            if m.matches(node.func, m.Name()):
                self.call_stack.pop()

        @m.visit(m.Arg(m.Name("baz") | m.Name("foobar")))
        def _count_args(self, node: cst.Arg) -> None:
            # See if the most shallow call is one we're interested in, so we can
            # count the args we care about only in calls we care about.
            if self.call_stack[-1] in self.functions:
                self.arg_count += 1

While there is more code than the previous example, it is arguably easier to understand and maintain each part of the code. It is also immune to any future changes to LibCST which change's the tree shape. Note that LibCST is traversing the tree completely in both cases, so while the first appears to be faster, it is actually doing the same amount of work as the second.

## Prefer `updated_node` when modifying trees

When you are using `~libcst.CSTTransformer` to modify a LibCST tree, only return modifications to `updated_node`. The `original_node` parameter on any `leave_<Node>` method is provided for book-keeping and is guaranteed to be equal via `==` and `is` checks to the `node` parameter in the corresponding `visit_<Node>` method. Remember that LibCST trees are immutable, so the only way to make a modification is to return a new tree. Hence, by the time we get to calling `leave_<Node>` methods, we have an updated tree whose children have been modified. Therefore, you should only return `original_node` when you want to explicitly discard changes performed on the node's children.

Say you wanted to rename all function calls which were calling global functions. So, you might write the following:

    class FunctionRenamer(cst.CSTTransformer):
        def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
            if m.matches(original_node.func, m.Name()):
                return original_node.with_changes(
                    func=cst.Name(
                        "renamed_" + cst.ensure_type(original_node.func, cst.Name).value
                    )
                )
            return original_node

Consider writing instead:

    class FunctionRenamer(cst.CSTTransformer):
        def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
            if m.matches(updated_node.func, m.Name()):
                return updated_node.with_changes(
                    func=cst.Name(
                        "renamed_" + cst.ensure_type(updated_node.func, cst.Name).value
                    )
                )
            return updated_node

The version that returns modifications to `original_node` has a subtle bug. Consider the following code snippet:

    some_func(1, 2, other_func(3))

Running the recommended transform will return us a new code snippet that looks like this:

    renamed_some_func(1, 2, renamed_other_func(3))

However, running the version which modifies `original_node` will instead return:

    renamed_some_func(1, 2, other_func(3))

That's because the `updated_node` tree contains the modification to `other_func`. By returning modifications to `original_node` instead of `updated_node`, we accidentally discarded all the work done deeper in the tree.

## Provide a `config` when generating code from templates

When generating complex trees it is often far easier to pass a string to `~libcst.parse_statement` or `~libcst.parse_expression` than it is to manually construct the tree. When using these functions to generate code, you should always use the `config` parameter in order to generate code that matches the defaults of the module you are modifying. The `~libcst.Module` class even has a helper attribute `~libcst.Module.config_for_parsing` to make it easy to use. This ensures that line endings and indentation are consistent with the defaults in the module you are adding the code to.

For example, to add a print statement to the end of a module:

    module = cst.parse_module(some_code_string)
    new_module = module.with_changes(
        body=(
            *module.body,
            cst.parse_statement(
                "print('Hello, world!')",
                config=module.config_for_parsing,
            ),
        ),
    )
    new_code_string = new_module.code

Leaving out the `config` parameter means that LibCST will assume some defaults and could result in added code which is formatted differently than the rest of the module it was added to. In the above example, because we used the config from the already-parsed example, the print statement will be added with line endings matching the rest of the module. If we neglect the `config` parameter, we might accidentally insert a windows line ending into a unix file or vice versa, depending on what system we ran the code under.

## Matchers

Matchers are provided as a way of asking whether a particular LibCST node and its children match a particular shape. It is possible to write a visitor that tracks attributes using `visit_<Node>` methods. It is also possible to implement manual instance checking and traversal of a node's children. However, both are cumbersome to write and hard to understand. Matchers offer a more concise way of defining what attributes on a node matter when matching against predefined patterns.

To accomplish this, a matcher has been created which corresponds to each LibCST node documented in `libcst-nodes`. Matchers default each of their attributes to the special sentinel matcher `~libcst.matchers.DoNotCare`. When constructing a matcher, you can initialize the node with only the values of attributes that you are concerned with, leaving the rest of the attributes set to `~libcst.matchers.DoNotCare` in order to skip comparing against them.

