# Wildcard Match

## Overview

Wildcard Match is a fnmatch-ish library originally created for [Rummage][rummage]. Normally using [fnmatch][fnmatch] or [glob][glob] is sufficient for most people's need, but with Rummage, we wanted a specific interface to be able to supply file name patterns, but also make it easy to exclude other file name patterns. For instance, if we wanted to match things like all `txt` **and** `py` files **except** `special.txt`, we wanted a simple pattern like:

```
*.txt|*.py|-special.txt
```

Wildcard Match, makes chaining patterns and supplying exclude patterns possible.

The interface for Wildcard match is very similar to fnmatch:

```pycon3
>>> import wcmatch as wcm
>>> wcm.fnmatch('test.txt', '*.txt|*.py|-special.txt')
True
>>> wcm.filter(['test.txt', 'test.py', 'test.bin', 'special.txt'], '*.txt|*.py|-special.txt')
['test.txt', 'test.py']
```

## Syntax

Out of the box, the syntax for Wilcard Match is just like fnmatch's with the addition of special handling for `|` and `-`.

Pattern  | Meaning
-------- | -------
`*`      | Matches everything.
`?`      | Matches any single character.
`[seq]`  | Matches any character in seq.
`[!seq]` | Matches any character not in seq.
`|`      | Separates multiple patterns.
`-`      | If used at the start of a pattern (start of string or directly following `|`), the pattern is treated as an exclusion pattern.

- In general, Wildcard Match has two types of patterns: **inclusion** and **exclusion**. You can chain these two patterns, or multiples of these two patterns, in any order with `|`.

- If at anytime an **exclusion** pattern is defined without an **inclusion** pattern, `*` is assumed as the **inclusion** pattern. This is because **exclusion** patterns are only applied to the results returned by the **inclusion** pattern. In simpler terms, **exclusion** patterns provide exceptions for **inclusions** patterns, so **exclusions** cannot exist without at least one **inclusion** pattern.

- `|` and `-` are ignored when inside a sequence `[-|]`. Be mindful that if `-` is in a sequence between to characters it is a range: `[a-z]` would match `a` through `z` while `[-a-z]` would match `-` **and** `a` through `z`.

- In general, Wildcard Match will apply case sensitive matching only if the system on which it is operating has a case sensitive file system, but if needed, Wildcard Match provides flags to explicitly set case sensitivity in which ever way is desired.

So let's look at some examples.

!!! example "Example - Chained Patterns"

    If we wanted to specify multiple file types, we could chain together the pattern `*.md` and `*.txt` with `|`.

    ```
    *.md|*.txt
    ```

    This will match all `md` and `txt` files.

    If we wanted to have a literal `|`, we simply enclose it in a sequence `[|]`.

    ```
    *[|]*.txt
    ```

    This will match any text file with `|` in its name.


!!! example "Example - Exclusion"

    If we wanted to look for all files but `*.bin`, we could create an exclusion pattern that starts with `-`. `-` only has special meaning at the beginning of a pattern.

    ```
    *|-*bin
    ```

    The following is equivalent to `*|-*bin` because when only an exclude pattern is provided, so the implied inclusion pattern is `*`.

    ```
    -*bin
    ```

    `-` will be treated normal if not at the start of a pattern or if included in a sequence (not as a range `[a-z]`). If we wanted to match the file name `-te-st.txt`, we could do the following:

    ```
    [-]te-st.txt
    ```

## Basic Usage

`#!py3 wcmatch.fnmatch(filename, pattern, flags=0)`
: 
    Takes a filename, a string pattern, and [flags](#flags).  Returns a boolean value that signifies whether the filename was matched by the pattern.

    ```pycon3
    >>> wcm.fnmatch('test.txt', '*.txt|*.py|-special.txt')
    True
    ```

`#!py3 wcmatch.filter(filenames, pattern, flags=0)`
: 
    Takes a list of filenames, a string pattern, and [flags](#flags). Returns a list of filenames that were appropriately matched by the pattern.

    ```pycon3
    >>> wcm.filter(['test.txt', 'test.py', 'test.bin', 'special.txt'], '*.txt|*.py|-special.txt')
    ['test.txt', 'test.py']
    ```

`#!py3 wcmatch.translate(pattern, flags=0)`
: 
    Takes a fnmatch pattern and [flags](#flags), and returns two strings converted to [re][] regular expression patterns that for the inclusion pattern and exclusion pattern respectively.

    ```pycon3
    >>> wcm.translate('*.txt|*.py|-special.txt')
    ('(?s:.*\\.txt|.*\\.py)\\Z', '(?s:special\\.txt)\\Z')
    ```

    Internally these are usually compiled to `#!py3 wcmatch.WcMatch(include, exclude=None)` objects.

    ```pycon3
    >>> import re
    >>> import wcmatch as wcm
    >>> filename = 'test.txt'
    >>> include, exclude = wcm.translate('*.txt|*.py|-special.txt')
    >>> wcm.WcMatch(re.compile(include), re.compile(exclude)).match(filename)
    True
    ```

## File Name Crawl

[Glob][glob] is a great library for crawling directories and getting file names, but sometimes it is difficult to crawl for exactly what you want without going the way of full regular expression. Essentially, Wildcard Match was created for `FnCrawl` as `fnmatch` just wasn't sufficient.

`FnCrawl` allows you to give a base directory, file name pattern, and a folder exclude pattern.  The file name pattern is applied to each file name that is found, while the folder exclude pattern is applied to each directory that is to be traversed. This allows you to traverse only the folders you want, and return only the files you want.

`#!py3 wcmatch.FnCrawl(base, pattern=None, exclude_pattern=None, recursive=False, show_hidden=False, flags=0)`
: 

    Class for crawling a directory and matching file names.

    Parameters                   | Description
    ---------------------------- | -----------
    `base`                       | Directory to start crawl.
    `pattern`                    | Fnmatch file name pattern.
    `exclude_pattern`            | Fnmatch file pattern specifying directories to exclude from crawl.
    `recursive`                  | Defines whether child folders should be traversed.
    `show_hidden`                | Defines whether hidden folders and files should be visible to the crawler.
    `flags`                      | [Flags](#flags) used to augment Wildcard Match behavior.

    Both the file name `pattern` and the folder `exclude_pattern` parameter operate on the base name of the respective file and directory that is found, not the full path name. If we had a `base` of `/some/path/` that had files `a.txt` and `b.txt` along with the `pattern` `*.txt`, the `pattern` would be applied to `a.txt`, not `/some/path/a.txt`. The same logic applies to child folders of `base` when considering `exclude_pattern`.

    While the folder `exclude_pattern` mentions **exclude**, you can easily change the logic to be inclusive instead with simple logic: `*|-test` which would exclude all folders *except* folders named test.

    !!! tip
        Patterns are generally compiled to `wcmatch.WcMatch(include, exclude=None)` objects.  `WcMatch` objects take up to two compiled regular expression objects. If for whatever reason you needed to use regular expression directly instead of a fnmatch pattern, you could directly feed your regular expression pattern(s) into a `WcMatch` object and pass the object directly as the value for `FnCrawl`'s `pattern` and/or `exclude_pattern` parameter.

        ```pycon3
        >>> pattern = wcm.WcMatch(re.compile('.*\.txt'))
        >>> [fn for fn in wcm.FnCrawl('./', pattern, recursive=True).match()]
        >>> ['./requirements/docs.txt', './requirements/lint.txt', './requirements/test.txt', './tests/dir_walker/a.txt', './tests/dir_walker/.hidden/a.txt']
        ```

    `#!py3 wcmatch.FnCrawl.match()`
    : 

        Begins crawling the directories and matching the file names.

        ```pycon3
        >>> [fn for fn in wcm.FnCrawl('./', '*.py|-setup.py', 'tests', recursive=True).match()]
        ['./wcmatch/__init__.py', './wcmatch/__version__.py', './wcmatch/file_hidden.py', './wcmatch/util.py', './wcmatch/wcparse.py']
        ```

    `#!py3 wcmatch.FnCrawl.imatch()`
    : 

        Like `match`, but returns an iterator.

        ```pycon3
        >>> [fn for fn in wcm.FnCrawl('./', '*.py|-setup.py', 'tests', recursive=True).match()]
        ['./wcmatch/__init__.py', './wcmatch/__version__.py', './wcmatch/file_hidden.py', './wcmatch/util.py', './wcmatch/wcparse.py']
        ```

    `#!py3 wcmatch.FnCrawl.get_skipped()`
    : 
        FnCrawl tracks the number of skipped files for informational purposes.  You can retrieve this count by calling this function.

    `#!py3 wcmatch.FnCrawl.kill()`
    : 
        Calling this function will terminate further crawling.  This could be run in `on_error` if desired.

    `#!py3 wcmatch.FnCrawl.reset()`
    : 
        Resets the kill switch in case you wish to rerun the crawl. Should be run before restarting via `match` or `imatch` if you previously called `kill`.

    `#!py3 wcmatch.FnCrawl.on_init(*args, **kwargs)`
    : 
        A hook for for adding additional initialization. Any `args` or `kwargs` not consumed by `__init__` will be passed to `on_init`.

    `#!py3 wcmatch.FnCrawl.on_validate_file(base, name)`
    : 
        A hook for adding additional validation of files. You could add checks to filter out files of a particular size or whatever other requirements you may have. Function should return a boolean signifying whether or not the file passed validation.

    `#!py3 wcmatch.FnCrawl.on_validate_directory(base, name)`
    : 
        A hook for adding additional validation that your project might have for potential directories to be crawled. Function should return a boolean signifying whether or not the directory passed validation.

    `#!py3 wcmatch.FnCrawl.on_match(base, name)`
    : 
        A hook for for additional logic when a file is matched. Here you can change what is returned by `match` and `imatch`. You could return a special record, just the file name, or anything else.

    `#!py3 wcmatch.FnCrawl.on_skip(base, name)`
    : 
        A hook for for additional logic when a file is skipped due to not passing validation. Anything (except `None`) returned by this function will also be returned by `match` and `imatch`.  You could create special skip records with information about the file that was skipped and return special match records in `on_match`, then you could check the record types returned by `match` or `imatch` and handle each object differently.

    `#!py3 wcmatch.FnCrawl.on_error(base, name)`
    : 
       A hook for when an error occurs during validation of a file or directory. This might be due to an access error, or any other reason. Here you could abort further crawling via `kill` if desired as errors are normally ignored. You could instead return error records to analyze later. Anything (except `None`) returned by this function will be returned by `match` or `imatch`.

## Flags

Wildcard Match provides a couple of flags to augment the current behavior of the file name matching.

`#!py3 wcmatch.NOEXTRA, wcmatch.N`
: 
    Special handling of `|` and `-` is the default behavior of Wildcard Match, but you disable this functionality by simply passing in the `NOEXTRA` flag.  So with `NOEXTRA` set, this would match:

    ```pycon3
    >>> wcm.fnmatch('-test|file.txt', '-test|file.txt', wcm.NOEXTRA)
    True
    ```

`#!py3 wcmatch.FORCECASE, wcmatch.F`
: 

    The host's file systems case sensitivity is initially detected and used as the default case sensitivity setting.  For instance on Window's, whose file system is not case sensitive, Wildcard Match does not use case sensitivity by default. By passing in the `FORCECASE` flag, all matches will be case sensitive. `FORCECASE` is mutually exclusive with [`IGNORECASE`](#ignorecase). So with `FORCECASE` passed in, the following would *not* match on both Windows and Linux/Unix systems:

    ```pycon3
    >>> wcm.fnmatch('TEST.txt', 'test.txt', wcm.FORCECASE)
    False
    ```

`#!py3 wcmatch.IGNORECASE, wcmatch.I`
: 

    The `IGNORECASE` flag is just like `FORCECASE` except that it forces case insensitive behavior regardless of what the host's file system behavior is. `IGNORECASE` is mutually exclusive with `FORCECASE`. So with `IGNORECASE` passed in, the following *would* match on both Windows and Linux/Unix systems:

    ```pycon3
    >>> wcm.fnmatch('TEST.txt', 'test.txt', wcm.IGNORECASE)
    True
    ```

`#!py3 wcmatch.RAWSTRING, wcmatch.R`
: 

    In certain applications, I was receiving strings from a GUI. So in a sense, I was receiving string representations of what I wanted, or something very similar to raw strings.  So in the interface, a user may want to insert a Unicode character with Unicode escape `\u0100` --> `Ā`. So they would enter in `\u0100.txt`, but what got sent back was `\\u0100.txt`, not `Ā`. Fnmatch would then match against the literal characters `\u0100` instead of the literal character `Ā`. I wanted to make this easier, and the idea of allowing an fnmatch that could take Python raw strings in code (`#!py3 r'\u0100.txt'`) was also an attractive option, especially when we talk about the `ESCAPE_CHARS` flag. Passing in `RAWSTRING` enables traditional string escapes in raw strings and Unicode escapes in Unicode raw strings.

    ```pycon3
    >>> wcm.fnmatch('Some\path\file_Ā.txt', r'Some\path\file_\u0100.txt', wcm.RAWSTRING)
    True
    ```

    You can also escape `\` if it is part of a string escape.

    ```pycon3
    >>> wcm.fnmatch('Some\path\File_\\u0100.txt', r'Some\path\File_\\u0100.txt', wcm.RAWSTRING)
    True
    ```

`#!py3 wcmatch.ESCAPES, wcmatch.E`
: 

    `ESCAPES` is a flag that augments the behavior of `\`. With `ESCAPES` passed in, `\` will escape whatever it is follows, even special fnmatch tokens, not just string escapes used in `RAWSTRING`.

    ```pycon3
    >>> wcm.fnmatch('Somepath*File_\\u0100.txt', r'Some\path\*File_\\u0100.txt', wcm.RAWSTRING | wcm.ESCAPES)
    True
    ```

--8<--
refs.md
--8<--
