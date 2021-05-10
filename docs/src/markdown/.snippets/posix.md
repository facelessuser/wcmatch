## POSIX Character Classes

A number of POSIX style character classes are available in the form `[:alnum:]`. They must be used inside sequences:
`[[:digit:]]`. The `C` locale is used, and the values for each character class are found in the table below.


Property   | Pattern
---------- | -------------------------------------------------
`alnum`    | `[a-zA-Z0-9]`
`alpha`    | `[a-zA-Z]`
`ascii`    | `[\x00-\x7F]`
`blank`    | `[ \t]`
`cntrl`    | `[\x00-\x1F\x7F]`
`digit`    | `[0-9]`
`graph`    | `[\x21-\x7E]`
`lower`    | `[a-z]`
`print`    | `[\x20-\x7E]`
`punct`    | ``[!\"\#$%&'()*+,\-./:;<=>?@\[\\\]^_`{}~]``
`space`    | `[ \t\r\n\v\f]`
`upper`    | `[A-Z]`
`word`     | `[a-zA-Z0-9_]`
`xdigit`   | `[A-Fa-f0-9]`
