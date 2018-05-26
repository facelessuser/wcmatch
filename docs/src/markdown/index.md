# Wildcard Match

## Overview

Wildcard Match is a fnmatch/glob library. It adds a number of features over the builtin Python fnmatch and glob. Fnmatch is file name matching centric while glob is path name matching/searching centric.

- Adds support for `**` in glob.
- Adds support for escaping characters with `\`.
- Adds support for brace expansion: `a{b,{c,d}}` --> `ab ac ad`.
- Adds support for extended match patterns: `@(...)`, `+(...)`, `!(...)`, etc.
- And more...

## Libraries

- [fnmatch](fnmatch): A filename matching library.
- [glob](glob): A file system searching and file path matching library.

--8<--
refs.md
--8<--
