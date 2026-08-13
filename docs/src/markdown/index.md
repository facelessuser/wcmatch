# Wildcard Match


> [!warning] Important Security Considerations!
> Learn more [here](#security-considerations), and be thoughtful about what you provide to this library in production
> systems.

## Overview

Wildcard Match translates the more simple, path-centric syntax of glob patterns to regular expression for the purpose of
iterating and matching file systems

Wildcard Match provides an enhanced [`fnmatch`](./fnmatch.md), [`glob`](./glob.md), and [`pathlib`](./pathlib.md)
library in order to provide file matching and globbing that more closely follows the features found in Bash. In some
ways these libraries are similar to Python's builtin libraries as they provide a similar interface to match, filter, and
glob the file system. But they also include a number of features found in Bash's globbing such as backslash escaping,
brace expansion, extended glob pattern groups, etc. They also add a number of new useful functions as well, such as
[`globmatch`](./glob.md#globmatch) which functions like [`fnmatch`](./fnmatch.md#fnmatch), but for paths.

Wildcard Match also adds a file search utility called [`wcmatch`](./wcmatch.md) that is built on top of
[`fnmatch`](./fnmatch.md#fnmatch) and [`globmatch`](./glob.md#globmatch). It was originally written for
[Rummage](https://github.com/facelessuser/Rummage), but split out into this project to be used by other projects that
may find its approach useful.

Bash is used as a guide when making decisions on behavior for [`fnmatch`](./fnmatch.md) and [`glob`](./glob.md).
Behavior may differ from Bash version to Bash version, but an attempt is made to keep Wildcard Match up with the latest
relevant changes. With all of this said, there may be a few corner cases in which we've intentionally chosen to not
*exactly* mirror Bash. If an issue is found where Wildcard Match seems to deviate in an illogical way, we'd love to hear
about it in the [issue tracker][issues].

## Features

A quick overview of Wildcard Match's Features:

-   Provides an interface comparable to Python's builtin in [`fnmatch`][fnmatch], [`glob`][glob], and
    [`pathlib`][pathlib].
-   Allows for a much more configurable experience when matching or globbing with many more features.
-   Adds support for `**` in glob.
-   Adds support for Zsh style `***` recursive glob for symlinks.
-   Adds support for escaping characters with `\`.
-   Add support for POSIX style character classes inside sequences: `[[:alnum:]]`, etc. The `C` locale is used.
-   Adds support for brace expansion: `a{b,{c,d}}` --> `ab ac ad`.
-   Adds support for expanding `~` or `~username` to the appropriate user path.
-   Adds support for extended match patterns: `@(...)`, `+(...)`, `*(...)`, `?(...)`, and `!(...)`.
-   Adds ability to match path names via the path centric `globmatch`.
-   Provides a [`pathlib`][pathlib] variant that uses Wildcard Match's `glob` library instead of Python's default.
-   Provides an alternative file crawler called `wcmatch`.
-   And more...

## Installation

Installation is easy with pip:

```console
$ pip install wcmatch
```

## Libraries

-   [`fnmatch`](./fnmatch.md): A file name matching library.
-   [`glob`](./glob.md): A file system searching and file path matching library.
-   [`pathlib`](./pathlib.md): A implementation of Python's `pathlib` that uses our own `glob` implementation.
-   [`wcmatch`](./wcmatch.md): An alternative file search library built on `fnmatch` and `globmatch`.

## Security Considerations

Wildcard Match makes globing with regular expressions easier and allows translation of the more simple, path-centric
syntax of glob patterns to regular expression for the purpose of iterating and matching file systems.

Regular expression engines like those in JavaScript, Python, Java, etc. choose compatibility and expressiveness over
guaranteed performance, accepting the risk of catastrophic backtracking when patterns contain nested quantifiers or
overlapping alternations.

ReDoS (Regular Expression Denial of Service) cases are those that specifically target the areas where a regular
expression engine does not guarantee optimal performance.

Because Wildcard Match builds its matching upon the Python regular expression engine, it can take advantage of the
engine's power, but is also susceptible to its weaknesses.

Wcmatch takes security seriously, and has taken many measures to reduce cases with less efficient patterns and
bottlenecks, but it is important to note that it will always be susceptible to some ReDoS cases because it is built on
an engine that is susceptible to ReDoS cases.

In general, we try to be transparent about features that we know, or later discover to be, susceptible to performance
based issues. Often, the more powerful and expressive the feature, the more susceptible it may be to such cases.

- `BRACES` is very powerful and allows a user to quickly generate many pattern combinations. With this power, a single
   pattern may expand into 10, 100, or even 10000 patterns. By default, we provide limits to pattern expansions, but
   users are responsible for setting limits that they find appropriate. If the risk of pattern expansions outweighs the
   usefulness for the given user, the feature is optional and does not need to be enabled.

- `EXTGLOB`/`EXTMATCH` allows for powerful groups of patterns that align with regular expression groups (e.g. `(...)+`,
   `(...)*`, `(...)?`, etc.). Extended glob patterns allow for more complex combinations without expanding a pattern
   into multiple patterns, but with this expressiveness comes the increased possibility of creating patterns that could
   cause overlapping alternations and/or catastrophic backtracking. The same rules for crafting good regular expression
   groups should be applied to extend glob patterns in the form: `@(...)`, `+(...)`, `*(...)`, `?(...)`, and `!(...)`.
   If running in an environment where the risk of sub-optimal performance is not tolerable, this behavior is optional
   and does not need to be enabled.

Restricting untrusted user pattern lengths and disabling features you don't need or do not want are the best ways to
improve performance. We do not limit input sizes ourselves and place that responsibility on the users of our library if
they desire to do so.

We will do our best to fix or reduce any issues brought to our attention, especially if the cost is reasonable to
address on our side, but for any issue that is not practical to fix on our side, and is explicitly caused by the regular
expression engine, we will redirect reports to this section within our documentation as our official answer.

Lastly, and to make things abundantly clear, if you create a performance critical system where you take user input and
use that input as the source of regular expression patterns, **you will be subject to performance based
vulnerabilities**. Please use this tool in appropriate environments to reduce the risk of exposure.
