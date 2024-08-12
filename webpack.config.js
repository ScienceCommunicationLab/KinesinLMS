/*** webpack.config.js ***/

/*  DMcQ:

    This config is meant to set up webpack to compile the library.js file containing KinesinLMS's components,
    and then copy that compiled library to the Django project where Django templates expect it to be.

 */

const path = require('path');

const kinesinlmsComponents = {
    entry: path.resolve(__dirname, "kinesinlms_components/src/kinesinlms-standard-components-index.ts"),
    devtool: "source-map",
    module: {
        rules: [
            {
                test: /\.(ts|js)x?$/,
                exclude: /node_modules/,
                use: [
                    {
                        loader: 'expose-loader',
                        options: {
                            exposes: {
                                globalName: 'kinesinlmsComponents',
                                override: true
                            }
                        }
                    },
                    {
                        loader: 'babel-loader',
                        options: {
                            presets: [
                                "@babel/preset-env",
                                "@babel/preset-react",
                                "@babel/preset-typescript",
                            ],
                        },
                    },
                ],
            },
            {
                test: /\.s[ac]ss$/i,
                use: [
                    // Creates `style` nodes from JS strings
                    "style-loader",
                    // Translates CSS into CommonJS
                    "css-loader",
                    // Compiles Sass to CSS
                    "sass-loader",
                ]
            }
        ]
    },
    resolve: {
        extensions: [".tsx", ".ts", ".jsx", ".js", ".json", ".sass", ".scss"],
    },
    output: {
        path: path.resolve(__dirname, 'kinesinlms/static/js'),
        filename: "kinesinlms-standard-course-components.bundle.js",
        sourceMapFilename: "kinesinlms-standard-course-components.bundle.js.map"
    },
    externals: {
        'react': 'React',
        'react-dom': 'ReactDOM',
        'i18next': 'i18next',
        'axios': 'axios'
    },
    watchOptions: {
        poll: true,
        ignored: /node_modules/,
    },
}

const kinesinlmsDiagramsComponents = {
    entry: path.resolve(__dirname, "kinesinlms_components/src/kinesinlms-diagrams-index.ts"),
    devtool: "source-map",
    module: {
        rules: [
            {
                test: /\.(ts|js)x?$/,
                exclude: /node_modules/,
                use: [
                    {
                        loader: 'expose-loader',
                        options: {
                            exposes: {
                                globalName: 'kinesinlmsDiagramsComponents',
                                override: true
                            }
                        }
                    },
                    {
                        loader: 'babel-loader',
                        options: {
                            presets: [
                                "@babel/preset-env",
                                "@babel/preset-react",
                                "@babel/preset-typescript",
                            ],
                        },
                    },
                ],
            },
            {
                test: /\.s[ac]ss$/i,
                use: [
                    // Creates `style` nodes from JS strings
                    "style-loader",
                    // Translates CSS into CommonJS
                    "css-loader",
                    // Compiles Sass to CSS
                    "sass-loader",
                ]
            }
        ]
    },
    resolve: {
        extensions: [".tsx", ".ts", ".jsx", ".js", ".json", ".sass", ".scss"],
    },
    output: {
        path: path.resolve(__dirname, 'kinesinlms/static/js'),
        filename: "kinesinlms-diagrams-components.bundle.js",
        sourceMapFilename: "kinesinlms-diagrams-components.bundle.js.map"
    },
    externals: {
        'react': 'React',
        'react-dom': 'ReactDOM',
        'i18next': 'i18next',
        'axios': 'axios'
    },
    watchOptions: {
        poll: true,
        ignored: /node_modules/,
    },
}

const kinesinlmsTabletoolComponents = {
    entry: path.resolve(__dirname, "kinesinlms_components/src/kinesinlms-tabletool-index.ts"),
    devtool: "source-map",
    module: {
        rules: [
            {
                test: /\.(ts|js)x?$/,
                exclude: /node_modules/,
                use: [
                    {
                        loader: 'expose-loader',
                        options: {
                            exposes: {
                                globalName: 'kinesinlmsTabletoolComponents',
                                override: true
                            }
                        }
                    },
                    {
                        loader: 'babel-loader',
                        options: {
                            presets: [
                                "@babel/preset-env",
                                "@babel/preset-react",
                                "@babel/preset-typescript",
                            ],
                        },
                    },
                ],
            },
            {
                test: /\.s[ac]ss$/i,
                use: [
                    // Creates `style` nodes from JS strings
                    "style-loader",
                    // Translates CSS into CommonJS
                    "css-loader",
                    // Compiles Sass to CSS
                    "sass-loader",
                ]
            }
        ]
    },
    resolve: {
        extensions: [".tsx", ".ts", ".jsx", ".js", ".json", ".sass", ".scss"],
    },
    output: {
        path: path.resolve(__dirname, 'kinesinlms/static/js'),
        filename: "kinesinlms-tabletool-components.bundle.js",
        sourceMapFilename: "kinesinlms-tabletool-components.bundle.js.map"
    },
    externals: {
        'react': 'React',
        'react-dom': 'ReactDOM',
        'i18next': 'i18next',
        'axios': 'axios'
    },
    watchOptions: {
        poll: true,
        ignored: /node_modules/,
    },
}


/*
"kinesinlmsProjectBundle" contains the js methods that useful for the entire kinesinLMS site.
They're mostly utility functions or things related to Bootstrap. These scripts
are loaded on *every* page, not just pages in the courses section.
*/

const kinesinlmsProjectBundle = {
    devtool: 'source-map',
    entry: path.resolve(__dirname, "kinesinlms/static/src/project.js"),
    output: {
        filename: "kinesinlms-project.bundle.js",
        path: path.resolve(__dirname, 'kinesinlms/static/js')
    },
    module: {
        rules: [
            {
                test: /\.css$/,
                use: ['style-loader', 'css-loader', 'sass-loader'],
            },
            {
                test: /\.scss$/,
                use: ['style-loader', 'css-loader', 'sass-loader'],
                // Handles .scss files and processes them with style-loader, css-loader, and sass-loader
            },
            {
                test: /\.js$/,
                exclude: /node_modules/,
                use: {
                    loader: "babel-loader",
                    options: {
                        presets: ['@babel/preset-env'],
                    },
                }
            }
        ]
    },
    watchOptions: {
        poll: true,
        ignored: /node_modules/,
    }
}


/*
"kinesinlmsCourseBundle" contains the more generic js methods that useful for the courses section.
These scripts are only loaded on course pages.
 */

const kinesinlmsCourseBundle = {
    devtool: 'source-map',
    entry: path.resolve(__dirname, "kinesinlms/static/src/course.js"),
    output: {
        filename: "kinesinlms-course.bundle.js",
        path: path.resolve(__dirname, 'kinesinlms/static/js')
    },
    module: {
        rules: [
            {
                test: /\.js$/,
                exclude: /node_modules/,
                use: {
                    loader: "babel-loader"
                }
            }
        ]
    },
    watchOptions: {
        poll: true,
        ignored: /node_modules/,
    }
}


/*
"kinesinlmsComposerBundle" contains js needed by composer.
 */

const kinesinlmsComposerBundle = {
    devtool: 'source-map',
    entry: path.resolve(__dirname, "kinesinlms/static/src/composer.ts"),
    output: {
        filename: "kinesinlms-composer.bundle.js",
        path: path.resolve(__dirname, 'kinesinlms/static/js')
    },
    resolve: {
        extensions: ['.ts', '.js'], // Added '.ts' extension for TypeScript files
    },
    module: {
        rules: [
            {
                test: /\.ts$/, // Updated test condition for TypeScript files
                exclude: /node_modules/,
                use: {
                    loader: "ts-loader", // Use ts-loader for TypeScript files
                }
            },
            {
                test: /\.js$/,
                exclude: /node_modules/,
                use: {
                    loader: "babel-loader"
                }
            }
        ]
    },
    watchOptions: {
        poll: true,
        ignored: /node_modules/,
    }
}


module.exports = [
    kinesinlmsProjectBundle,
    kinesinlmsCourseBundle,
    kinesinlmsComponents,
    kinesinlmsDiagramsComponents,
    kinesinlmsTabletoolComponents,
    kinesinlmsComposerBundle
]
