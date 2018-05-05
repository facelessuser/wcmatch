# Wildcard Match

## Overview

Wildcard Match is a fnmatch-ish library originally created for [Rummage][rummage]. Normally using [fnmatch][fnmatch] or [glob][glob] is sufficient for most people's need, but with Rummage, we wanted a specific interface to be able to supply file name patterns, but also make it easy to exclude other file name patterns. For instance, if we wanted to match things like all `txt` **and** `py` files **except** `special.txt`, we wanted a simple pattern like:

```
*.txt|*.py|-special.txt
```

With Wildcard Match, this is exactly what you do.

## Why an Alternative FnMatch?

It could easily be argued that if fnmatch won't do what you want, you could just use regular expression. But what if you are using input from a user interface and you are targeting users that may not be familiar with regular expression? Fnmatch provides a lower bar of entry for filename pattern matching, but in some ways, it is a bit too limited.

Traditionally fnmatch allows you to provide ranges of characters with `[seq]` and exclude certain characters via `[!seq]`. But if you wanted to specifically match something like `*.md` **and** `*.txt`, using `[seq]` and `[!seq]` would be awkward, and most likely inadequate. So how would you get this functionality out of one pattern? You'd have to essentially run two different calls, so you could split on an arbitrary character like `,`. So if you had `*.md,*.txt` it would split into `*.md` and `*.txt` and run each separately through fnmatch. But what if your file name had a `,` in its name? If we had `apples, and oranges.txt,instructions.txt`, we'd get `apples`, ` and oranges.txt`, and `instructions.txt`. You'd need context, so naively splitting on an a character would have surprising behavior in certain cases.

Let's take this further. What if you wanted to match all files except a specific type? You'd really need an inverse matching function.  But taking it even furhter, what if we wanted to match all text files except `special.txt`?  This would really require a convoluted pattern.

Wildcard Match solves this issue by adding special meaning to `|` and `-` in an fnmatch pattern.  This allows for simple patterns to achieve a bit more complex logic without having to go full regular expression. Let's illustrate this with some of our mentioned examples earlier.

With wild card match we can easily match things like all `txt` **and** `py` files except `special.txt`:

```
*.txt|*.py|-special.txt
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

In general, Wildcard Match has two types of patterns: **inclusion** and **exclusion**. You can chain these multiples of these patterns in any order with `|`.

If at anytime an **exclusion** pattern is defined without an **inclusion** pattern, `*` is assumed as the inclusion pattern. This is because **exclusion** patterns are only applied to the results returned by the **inclusion** pattern. In simpler terms, **exclusion** patterns provide exceptions for **inclusions** patterns, so **exclusions** cannot exist without at least one **inclusion** pattern.

`|` and `-` are ignored when inside a sequence `[-|]`. Be mindful that if `-` is in a sequence between to characters it is a range: `[a-z]` would match `a` through `z` while `[-a-z]` would match `-` **and** `a` through `z`.

In general, Wildcard match will apply case sensitive matching only if the system on which it is operating has a case sensitive file system, but if needed, Wildcard Match provides flags to explicitly case sensitivity in which ever way is required.

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

## Special Flags

Wildcard Match provides a couple of flags to augment the current behavior of the file name matching.

Flags | Description
----- | -----------
`NO_EXTRA` | Disables special handling of `|` and `-`
`CASE`     | Explicitly enable case sensitivity regardless of the host file system's sensitivity.
`IGNORECASE` | Explicitly disable case sensitivity regardless of the host file system's sensitivity.
`RAW_STRING_ESCAPES` | This will handle all normal string escapes (`\t`, `\v`, `\x00`, etc.) in a raw string and additionally Unicode string escapes in a raw Unicode string (`\u0000`, `\U0000`, `\N{UNICODE NAME}`).
`ESCAPE_CHARS` | This will require cause `\` to escape any character.

--8<--
refs.md
--8<--
