# Wildcard Match (WIP)

Wildcard Match is a fnmatch/glob library. It adds a number of features over the builtin Python fnmatch and glob. Fnmatch is file name matching centric, while glob is path name matching/searching centric.

- Adds support for `**` in glob.
- Adds support for escaping characters with `\`.
- Adds support for brace expansion: `a{b,{c,d}}` --> `ab ac ad`.
- Adds support for extended match patterns: `@(...)`, `+(...)`, `!(...)`, etc.
- Adds ability to match path names via globmatch as well as traditional file system searching via glob.
- And more...

## Documentation

http://facelessuser.github.io/wcmatch/

## License

The MIT License (MIT)

Copyright (c) 2018 Isaac Muse

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
