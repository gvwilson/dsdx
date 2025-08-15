# Contributing

Contributions are very welcome;
please contact us [by email][email] or by filing an issue in [our repository][repo].
All contributors must abide by our Code of Conduct.

## Setup and Operation

-   Install [uv][uv].
-   Create a virtual environment by running `uv venv` in the root directory.
-   Activate it by running `source .venv/bin/activate` in your shell.
-   Install dependencies by running `uv sync`.
-   Run `make` on its own to see a list of common commands.

| make task | effect                            |
| --------- | ----------------------------------|
| build     | render HTML pages                 |
| clean     | clean up                          |
| commands  | show available commands (default) |
| links     | check links in published site     |
| lint      | check structure and content       |
| serve     | serve generated HTML              |
| spelling  | check for unknown words           |

## Structure

-   Lessons are in `nn_slug` directories
    -   `nn` is two-digit sequence number
    -   `slug` is short mnemonic
    -   Each lesson must have an `index.md` file containing its content
-   Diagrams should be SVG files created with [draw.io][draw-io]
-   `bibliography/index.md` has the bibliography as a definition list
    -   Citation keys have IDs for linking
    -   Use an inline HTML link `b:key` in files to create links
-   `glossary/index.md` has the glossary as definition list
    -   Reference keys have IDs for linking
    -   Use an inline HTML link `g:key` in files to create links
-   The `static` directory contains static files
-   The `templates` directory contains [Jinja][jinja] templates used to generate HTML
    -   `page.html` is used for website pages

## FAQ

Do you need help?
:   Yes—please see the issues in [our repository][repo].

What sort of feedback would be useful?
:   Everything is welcome,
    from pointing out mistakes to suggestions for better explanations.

Can I add a new section?
:   Possibly, but please [reach out][email] before doing so.

Why is this material free?
:   Because if we all give a little, we all get a lot.

[draw-io]: https://www.drawio.com/
[email]: mailto:gvwilson@third-bit.com
[jinja]: https://jinja.palletsprojects.com/
[repo]: https://github.com/gvwilson/dsdx
[uv]: https://github.com/astral-sh/uv
