# Styles

KinesinLMS uses Bootstrap 5.3 for basic styles and layout.

Additional styles are defined in the `kinesinlms/static/scss` directory.
These styles are collected into one `project.scss` file, which is compiled into `kinesinlms/static/css/project.css`
via sass.

## Compiling Styles

Prerequisite: You must have `sass` installed and availble on the command line.

To compile the styles, run the following command from base project directory.

```bash
sass --watch kinesinlms/static/scss:kinesinlms/static/css --style compressed --load-path=node_modules
```

This command is also available in the `package.json` file as the `watch-styles` script. To run it from the root of the
project, use:

```bash
npm run watch-styles
```



