# Changelog

```diff
@@ -2,7 +2,6 @@
   This file was automatically generated - do not edit
 -#}
 {% import "partials/language.html" as lang with context %}
-{% set feature = config.theme.feature %}
 {% set palette = config.theme.palette %}
 {% set font = config.theme.font %}
 <!doctype html>
@@ -30,19 +29,6 @@
       {% elif config.site_author %}
         <meta name="author" content="{{ config.site_author }}">
       {% endif %}
-      {% for key in [
-        "clipboard.copy",
-        "clipboard.copied",
-        "search.language",
-        "search.pipeline.stopwords",
-        "search.pipeline.trimmer",
-        "search.result.none",
-        "search.result.one",
-        "search.result.other",
-        "search.tokenizer"
-      ] %}
-        <meta name="lang:{{ key }}" content="{{ lang.t(key) }}">
-      {% endfor %}
       <link rel="shortcut icon" href="{{ config.theme.favicon | url }}">
       <meta name="generator" content="mkdocs-{{ mkdocs_version }}, mkdocs-material-5.0.0b2-1">
     {% endblock %}
@@ -56,9 +42,9 @@
       {% endif %}
     {% endblock %}
     {% block styles %}
-      <link rel="stylesheet" href="{{ 'assets/stylesheets/application.********.css' | url }}">
+      <link rel="stylesheet" href="{{ 'assets/stylesheets/main.********.min.css' | url }}">
       {% if palette.primary or palette.accent %}
-        <link rel="stylesheet" href="{{ 'assets/stylesheets/application-palette.********.css' | url }}">
+        <link rel="stylesheet" href="{{ 'assets/stylesheets/palette.********.min.css' | url }}">
       {% endif %}
       {% if palette.primary %}
         {% import "partials/palette.html" as map %}
@@ -69,20 +55,17 @@
       {% endif %}
     {% endblock %}
     {% block libs %}
-      <script src="{{ 'assets/javascripts/modernizr.********.js' | url }}"></script>
     {% endblock %}
     {% block fonts %}
       {% if font != false %}
         <link href="https://fonts.gstatic.com" rel="preconnect" crossorigin>
         <link rel="stylesheet" href="https://fonts.googleapis.com/css?family={{
             font.text | replace(' ', '+') + ':300,400,400i,700%7C' +
             font.code | replace(' ', '+')
           }}&display=fallback">
         <style>body,input{font-family:"{{ font.text }}","Helvetica Neue",Helvetica,Arial,sans-serif}code,kbd,pre{font-family:"{{ font.code }}","Courier New",Courier,monospace}</style>
       {% endif %}
     {% endblock %}
-    <link rel="stylesheet" href="{{ 'assets/fonts/material-icons.css' | url }}">
     {% if config.extra.manifest %}
       <link rel="manifest" href="{{ config.extra.manifest | url }}" crossorigin="use-credentials">
     {% endif %}
@@ -95,47 +78,46 @@
     {% endblock %}
     {% block extrahead %}{% endblock %}
   </head>
+  {% set direction = config.theme.direction | default(lang.t('direction')) %}
   {% if palette.primary or palette.accent %}
     {% set primary = palette.primary | replace(" ", "-") | lower %}
     {% set accent  = palette.accent  | replace(" ", "-") | lower %}
-    <body dir="{{ lang.t('direction') }}" data-md-color-primary="{{ primary }}" data-md-color-accent="{{ accent }}">
+    <body dir="{{ direction }}" data-md-color-primary="{{ primary }}" data-md-color-accent="{{ accent }}">
   {% else %}
-    <body dir="{{ lang.t('direction') }}">
+    <body dir="{{ direction }}">
   {% endif %}
-    <svg class="md-svg">
-      <defs>
-        {% set platform = config.extra.repo_icon or config.repo_url %}
-        {% if "github" in platform %}
-          {% include "assets/images/icons/github.f0b8504a.svg" %}
-        {% elif "gitlab" in platform %}
-          {% include "assets/images/icons/gitlab.6dd19c00.svg" %}
-        {% elif "bitbucket" in platform %}
-          {% include "assets/images/icons/bitbucket.1b09e088.svg" %}
-        {% endif %}
-      </defs>
-    </svg>
     <input class="md-toggle" data-md-toggle="drawer" type="checkbox" id="__drawer" autocomplete="off">
     <input class="md-toggle" data-md-toggle="search" type="checkbox" id="__search" autocomplete="off">
-    <label class="md-overlay" data-md-component="overlay" for="__drawer"></label>
+    <label class="md-overlay" for="__drawer"></label>
     {% if page.toc | first is defined %}
-      <a href="{{ (page.toc | first).url }}" tabindex="0" class="md-skip">
+      {% set skip = page.toc | first %}
+      <a href="{{ skip.url | url }}" class="md-skip" data-md-component="skip">
         {{ lang.t('skip.link.title') }}
       </a>
     {% endif %}
+    {% if self.announce() %}
+      <aside class="md-announce" data-md-component="announce">
+        <div class="md-announce__inner md-grid md-typeset">
+          {% block announce %}{% endblock %}
+        </div>
+      </aside>
+    {% endif %}
     {% block header %}
       {% include "partials/header.html" %}
     {% endblock %}
-    <div class="md-container">
+    <div class="md-container" data-md-component="container">
       {% block hero %}
         {% if page and page.meta and page.meta.hero %}
           {% include "partials/hero.html" with context %}
         {% endif %}
       {% endblock %}
-      {% if feature.tabs %}
-        {% include "partials/tabs.html" %}
-      {% endif %}
+      {% block tabs %}
+        {% if "tabs" in config.theme.features %}
+          {% include "partials/tabs.html" %}
+        {% endif %}
+      {% endblock %}
-      <main class="md-main" role="main">
-        <div class="md-main__inner md-grid" data-md-component="container">
+      <main class="md-main" data-md-component="main">
+        <div class="md-main__inner md-grid">
           {% block site_nav %}
             {% if nav %}
               <div class="md-sidebar md-sidebar--primary" data-md-component="navigation">
@@ -160,41 +142,25 @@
             <article class="md-content__inner md-typeset">
               {% block content %}
                 {% if page.edit_url %}
-                  <a href="{{ page.edit_url }}" title="{{ lang.t('edit.link.title') }}" class="md-icon md-content__icon">&#xE3C9;</a>
+                  <a href="{{ page.edit_url }}" title="{{ lang.t('edit.link.title') }}" class="md-content__button md-icon">
+                    {% include ".icons/material/pencil.svg" %}
+                  </a>
                 {% endif %}
+                {% block source %}
+                  {% if page and page.meta and page.meta.source %}
+                    {% include "partials/source-link.html" %}
+                  {% endif %}
+                {% endblock %}
                 {% if not "\x3ch1" in page.content %}
                   <h1>{{ page.title | default(config.site_name, true)}}</h1>
                 {% endif %}
                 {{ page.content }}
-                {% block source %}
-                  {% if page and page.meta and page.meta.source %}
-                    <h2 id="__source">{{ lang.t("meta.source") }}</h2>
-                    {% set repo = config.repo_url %}
-                    {% if repo | last == "/" %}
-                      {% set repo = repo[:-1] %}
-                    {% endif %}
-                    {% set path = page.meta.path | default([""]) %}
-                    {% set file = page.meta.source %}
-                    <a href="{{ [repo, path, file] | join('/') }}" title="{{ file }}" class="md-source-file">
-                      {{ file }}
-                    </a>
-                  {% endif %}
-                {% endblock %}
+                {% if page and page.meta %}
+                  {% if page.meta.git_revision_date_localized or
+                        page.meta.revision_date
+                  %}
+                    {% include "partials/source-date.html" %}
-                {% if page and page.meta and (
-                      page.meta.git_revision_date_localized or
-                      page.meta.revision_date
-                ) %}
-                  {% set label = lang.t("source.revision.date") %}
-                  <hr>
-                  <div class="md-source-date">
-                    <small>
-                      {% if page.meta.git_revision_date_localized %}
-                        {{ label }}: {{ page.meta.git_revision_date_localized }}
-                      {% elif page.meta.revision_date %}
-                        {{ label }}: {{ page.meta.revision_date }}
-                      {% endif %}
-                    </small>
-                  </div>
                 {% endif %}
               {% endblock %}
               {% block disqus %}
@@ -208,29 +174,40 @@
         {% include "partials/footer.html" %}
       {% endblock %}
     </div>
+    {% block config %}
+      <script>var __config={}</script>
+    {% endblock %}
     {% block scripts %}
-      <script src="{{ 'assets/javascripts/application.df00da5d.js' | url }}"></script>
-      {% if lang.t("search.language") != "en" %}
-        {% set languages = lang.t("search.language").split(",") %}
-        {% if languages | length and languages[0] != "" %}
-          {% set path = "assets/javascripts/lunr/" %}
-          <script src="{{ (path ~ 'lunr.stemmer.support.js') | url }}"></script>
-          {% for language in languages | map("trim") %}
-            {% if language != "en" %}
-              {% if language == "ja" %}
-                <script src="{{ (path ~ 'tinyseg.js') | url }}"></script>
-              {% endif %}
-              {% if language in ("ar", "da", "de", "es", "fi", "fr", "hu", "it", "ja", "nl", "no", "pt", "ro", "ru", "sv", "th", "tr", "vi") %}
-                <script src="{{ (path ~ 'lunr.' ~ language ~ '.js') | url }}"></script>
-              {% endif %}
-            {% endif %}
-          {% endfor %}
-          {% if languages | length > 1 %}
-            <script src="{{ (path ~ 'lunr.multi.js') | url }}"></script>
-          {% endif %}
-        {% endif %}
-      {% endif %}
-      <script>app.initialize({version:"{{ mkdocs_version }}",url:{base:"{{ base_url }}"}})</script>
+      <script src="{{ 'assets/javascripts/vendor.31a2e7b9.min.js' | url }}"></script>
+      <script src="{{ 'assets/javascripts/bundle.5b33ad8d.min.js' | url }}"></script>
+      {%- set translations = {} -%}
+      {%- for key in [
+        "clipboard.copy",
+        "clipboard.copied",
+        "search.config.lang",
+        "search.config.pipeline",
+        "search.config.separator",
+        "search.result.placeholder",
+        "search.result.none",
+        "search.result.one",
+        "search.result.other"
+      ] -%}
+        {%- set _ = translations.update({ key: lang.t(key) }) -%}
+      {%- endfor -%}
+      <script id="__lang" type="application/json">
+        {{ translations | tojson }}
+      </script>
+      <script>
+        __material = initialize(Object.assign({
+          url: {
+            base: "{{ base_url }}",
+            worker: {
+              search: "{{ 'assets/javascripts/worker/search.edc88caf.min.js' | url }}"
+            }
+          },
+          features: {{ config.theme.features | tojson }}
+        }, __config))
+      </script>
       {% for path in config["extra_javascript"] %}
         <script src="{{ path | url }}"></script>
       {% endfor %}
```

## 6.0.1

- **FIX**: If we only have one pattern (exclusion patterns not included) we can disable unique path filtering on returns
  as you cannot have a duplicate path with only one inclusion pattern.

## 6.0

- **NEW**: Tilde user expansion support via the new `GLOBTILDE` flag.
- **NEW**: `glob` by default now returns only unique results, regardless of whether multiple patterns that match the
  same file were provided, or even when `BRACE` or `SPLIT` expansion produces new patterns that match the same file.
- **NEW**: A new flag called `NOUNIQUE` has been added that makes `glob` act like Bash, which will return the same file
  multiple times if multiple patterns match it, whether provided directly or due to the result of `BRACE` or `SPLIT`
  expansion.
- **NEW**: Limit number of patterns that can be processed (expanded and otherwise) to 1000. Allow user to change this
  value via an optional `limit` parameter in related API functions.
- **FIX**: Matching functions that receive multiple patterns, or that receive a single pattern that expands to multiple,
  will filter out duplicate patterns in order avoid redundant matching. While the `WcMatch` class crawls the file
  system, it utilizes the aforementioned matching functions in it's operation, and indirectly takes advantage of this.
  `glob` (and related functions: `rglob`, `iglob`, etc.) will also filter redundant patterns except when `NOUNIQUE` is
  enabled, this is so they can better act like Bash when `NOUNIQUE` is enabled.
- **FIX**: `BRACE` is now processed before `SPLIT` in order to fix a number of edge cases.
- **FIX**: `RAWCHARS` was inconsistently applied at different times depending on what was calling it. It is now applied
  first followed by `BRACE`, `SPLIT`, and finally `GLOBTILDE`.

## 5.1.0

- **NEW**: Add new parameter to `glob` related functions (except in `pathlib`) called `root_dir` that allows a user to
  specify a different working directory with either a string or path-like object. Path-like inputs are only supported on
  Python 3.6+.
- **NEW**: Support path-like objects for `globmatch` and `globfilter` path inputs. Path-like inputs are only supported
  on Python 3.6+.
- **FIX**: Filter functions should not alter the slashes of files it filters. Filtered strings and paths should be
  returned unaltered.

## 5.0.3

- **FIX**: Rework `glob` relative path handling so internally it is indistinguishable from when it is given no relative
  path and uses the current working directory. This fixes an issue where `pathlib` couldn't handle negate patterns
  properly (`!negate`).

## 5.0.2

- **FIX**: Fix case where a `GLOBSTAR` pattern, followed by a slash, was not disabling `MATCHBASE`.
- **FIX**: Fix `pathlib` relative path resolution in glob implementations.

## 5.0.1

- **FIX**: In `glob`, avoid using up too many file descriptors by acquiring all file/folder names under a directory in
  one batch before recursing into other folders.

## 5.0

- **NEW**: Add `wcmatch.pathlib` which contains `pathlib` variants that uses `wcmatch.glob` instead of the default
  Python glob.
- **NEW**: `escape` and `raw_escape` can manually be forced to use Windows or Linux/Unix logic via the keyword only
  argument by setting to `False` or `True` respectively. The default is `None` which will auto detect the system.
- **NEW**: The deprecated flag `FORCECASE` has now been removed.
- **NEW**: The deprecated functions `globsplit` and `fnsplit` have been removed.
- **NEW**: The deprecated variables `version` and `version_info` have been removed.

## 4.3.1

- **FIX**: Regression for root level literal matches in `glob`.
- **FIX**: Bug where `glob` would mistakenly abort if a pattern started with a literal file or directory and could not
  match a file or directory. This caused subsequent patterns in the chain to not get evaluated.

## 4.3.0

- **NEW**: Add `CASE` flag which allows for case sensitive paths on Linux, macOS, and Windows. Windows drive letters and
  UNC `//host-name/share-name/` portion are still treated insensitively, but all directories will be treated with case
  sensitivity.
- **NEW**: With the recent addition of `CASE` and `FORCEUNIX`, `FORCECASE` is no longer needed. Deprecate `FORCECASE`
  which will be removed at some future point.

## 4.2.0

- **NEW**: Drop Python 3.4 support.
- **NEW**: Add flags `FORCEWIN` and `FORCEUNIX` to force Windows or Linux/Unix path logic on commands that do not access
  the file system: `translate`, `fnmatch`, `filter`, `globmatch`, `globfilter`, etc. These flags will not work with
  `glob`, `iglob` or with the `WcMatch` class. It also will not work when using the `REALPATH` flag with things like
  `fnmatch`, `filter`, `globmatch`, `globfilter`.
- **FIX**: `glob` corner case where the first folder, if defined as a literal name (not a magic pattern), would not be
  treated properly if `IGNORECASE` was enabled in Linux.

## 4.1.0

- **NEW**: Add `WcMatch.is_aborted`.
- **FIX**: Remove deprecation of `kill` and `reset` in `WcMatch`. There are legitimate reasons to not deprecate killing
  via `kill` instead of simply breaking.
- **FIX**: If for any reason, a file exists, but fails "is directory" check, consider it as a file.

## 4.0.1

- **FIX**: Fix regression with exclusion patterns that use braces in `glob`.
- **FIX**: Translate functions should have `NODIR` patterns exclude if matched not exclude if not matched.

## 4.0

- **NEW**: Deprecated `WcMatch` class methods `kill` and `reset`. `WcMatch` should be broken with a simple `break`
  statement instead.
- **NEW**: Add a new flag `MARK` to force `glob` to return directories with a trailing slash.
- **NEW**: Add `MATCHBASE` that causes glob glob related functions and `WcMatch`, when the pattern has no slashes in it,
  to seek for any file anywhere in the tree with a matching basename.
- **NEW**: Add `NODIR` that causes `glob` matchers and crawlers to only match and return files.
- **NEW**: Exclusion patterns (enabled with `NEGATE`) now always enable `DOTALL` in the exclusion patterns. They also
  will match symlinks in `**` patterns. Only non `NEGATE` patterns that are paired with a `NEGATE` pattern are subject
  to symlinks and dot rules. Exclusion patterns themselves allow dots and symlinks to make filtering easier.
- **NEW**: Exclusion patterns no longer provide a default inclusion pattern if one is not specified. Exclusion patterns
  are meant to filter the results of inclusion patterns. You can either use the `SPLIT` flag and provide an inclusion
  pattern with your default ('default_pattern|!exclusion'), or feed in a list of multiple patterns instead of a single
  string (`['inclusion', '!exclusion']`). If you really need the old behavior, you can use the `NEGATEALL` flag which
  will provide a default inclusion pattern that matches all files.
- **NEW**: Translate now outputs exclusion patterns so that if they match, the file is excluded. This is opposite logic
  to how it used to be, but is more efficient.
- **FIX**: An empty pattern in `glob` should not match slashes.

## 3.0.2

- **FIX**: Fix an offset issue when processing an absolute path pattern in `glob` on Linux or macOS.
- **FIX**: Fix an issue where the `glob` command would use `GLOBSTAR` logic on `**` even when `GLOBSTAR` was disabled.

## 3.0.1

- **FIX**: In the `WcMatch` class, defer hidden file check until after the file or directory is compared against
  patterns to potentially avoid calling hidden if the pattern doesn't match. The reduced `lstat` calls improve
  performance.

## 3.0

- **NEW**: `globsplit` and `fnsplit` have been deprecated. Users are encouraged to use the new `SPLIT` flag to allow
  functions to use multiple wildcard paths delimited by `|`.
- **NEW**: `globmatch` and `globfilter` will now parse provided paths as real paths if the new `REALPATH` flag is set.
  This has the advantage of allowing the commands to be aware of symlinks and properly apply related logic (whether to
  follow the links or not). It also helps to clarify ambiguous cases where it isn't clear if a file path references a
  directory because the trailing slash was omitted. It also allows the command to be aware of Windows drives evaluate
  the path in proper context compared to the current working directory.
- **NEW**: `WcMatch` class no longer accepts the `recursive` or `show_hidden` parameter, instead the `RECURSIVE` or
  `HIDDEN` flag must be used.
- **NEW**: `WcMatch` class now can search symlink directories with the new `SYMLINK` flag.
- **NEW**: `glob` and `iglob` functions now behave like Bash 5.0 in regards to symlinks in `GLOBSTAR` (`**`). `GLOBSTAR`
  will ignore symlink directories. This affects other functions such as `globmatch` and `globfilter` when the `REALPATH`
  flag is enabled.
- **NEW**: New flag called `FOLLOW` was added to force related `glob` commands to recognize and follow symlink
  directories.
- **FIX**: Fix `glob` regression where inverse patterns such as `!**/test/**` would allow a directory `base/test` to
  match when it should have excluded it.
- **FIX**: `glob` should handle root paths (`/`) properly, and on Windows, it should assume the drive of the current
  working directory.

## 2.2.1

- **FIX**: `EXTMATCH`/`EXTGLOB` should allow literal dots and should not treat dots like sequences do.
- **FIX**: Fix `!(...)` extended match patterns in `glob` and `globmatch` so that they properly match `.` and `..` if
  their pattern starts with `.`.
- **FIX**: Fix `!(...)` extended match patterns so that they handle path separators correctly.
- **FIX**: Patterns such as `?` or `[.]` should not trigger matching directories `.` and `..` in `glob` and `globmatch`.

## 2.2.0

- **NEW**: Officially support Python 3.8.

## 2.1.0

- **NEW**: Deprecate `version` and `version_info` in favor of the more standard `__version__` and `__version_info__`.
- **FIX**: Fix issue where exclusion patterns would trigger before end of path.
- **FIX**: Fix `GLOBSTAR` regular expression pattern issues.

## 2.0.3

- **FIX**: In `glob`, properly handle files in the current working directory when give a literal pattern that matches
  it.

## 2.0.2

- **FIX**: `wcmatch` override events (`on_error` and `on_skip`) should verify the return  is **not None** and not **not
  falsy**.

## 2.0.1

- **FIX**: Can't install due to requirements being assigned to setup opposed to install.

## 2.0

!!! danger "Breaking Changes"
    Version 2.0 introduces breaking changes in regards to flags.  This is meant to bring about consistency amongst the
    provided libraries. Flag names have been changed in some cases, and logic has been inverted in some cases.

- **NEW**: Glob's `NOBRACE`, `NOGLOBSTAR`, and `NOEXTGLOB` flags are now `BRACE`, `GLOBSTAR`, and `EXTGLOB` and now
  enable the features instead of disabling the features. This logic matches the provided `fnmatch` and `wcmatch`.
- **NEW**: Glob's `DOTGLOB` and `EXTGLOB` also have the respective aliases `DOTMATCH` and `EXTMATCH` to provide
  consistent flags across provided libraries, but the `GLOB` variants that match Bash's feature names can still be used.
- **NEW**: `fnmatch`'s `PERIOD` flag has been replaced with `DOTMATCH` with inverted logic from what was originally
  provided.
- **NEW**: Documentation exposes the shorthand form of flags: `FORCECASE` --> `F`, etc.
- **FIX**: Wcmatch always documented that it had the flag named `EXTMATCH`, but internally it was actually `EXTGLOB`,
  this was a bug though. `EXTMATCH` is now the documented and the actual flag to use.

## 1.0.2

- **FIX**: Officially support Python 3.7.

## 1.0.1

- **FIX**: Ensure that all patterns in `glob` that have a directory preceding `**` but also end with `**` returns the
  preceding directory.
- **FIX**: Fix byte conversion in path normalization.
- **FIX**: Ensure POSIX character classes, when at the start of a sequence, properly have hyphens escaped following it.
  `[[:ascii:]-z]` should convert to `[\x00-\x7f\\-b]` not `[\x00-\x7f-b]`.
- **FIX**: Fix an issue where we would fail because we couldn't covert raw characters even though raw character parsing
  was disabled.
- **FIX**: Better default for file patterns.  Before if no pattern was provided for files, `'*'` was assumed, now it is
  `''`, and if `''` is used, all files will be matched. This works better for when full path is enabled as you get the
  same file matching logic.

## 1.0

- Initial release

--8<-- "refs.txt"
