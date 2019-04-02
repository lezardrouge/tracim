const path = require('path')
const isProduction = process.env.NODE_ENV === 'production'

console.log('isProduction : ', isProduction)

module.exports = {
  mode: isProduction ? 'production' : 'development',
  entry: [],
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: isProduction ? 'caldavzap.app.js' : 'caldavzap.app.dev.js',
    pathinfo: !isProduction,
    library: isProduction ? 'appCaldavzap' : undefined,
    libraryTarget: isProduction ? 'var' : undefined
  },
  externals: {},
  // isProduction ? { // Côme - since plugins are imported through <script>, cannot externalize libraries
  //   react: {commonjs: 'react', commonjs2: 'react', amd: 'react', root: '_'},
  //   'react-dom': {commonjs: 'react-dom', commonjs2: 'react-dom', amd: 'react-dom', root: '_'},
  //   classnames: {commonjs: 'classnames', commonjs2: 'classnames', amd: 'classnames', root: '_'},
  //   'prop-types': {commonjs: 'prop-types', commonjs2: 'prop-types', amd: 'prop-types', root: '_'},
  //   tracim_frontend_lib: {commonjs: 'tracim_frontend_lib', commonjs2: 'tracim_frontend_lib', amd: 'tracim_frontend_lib', root: '_'}
  // }
  // : {},
  devServer: {
    contentBase: path.join(__dirname, '.'),
    // contentBase: path.join(__dirname, 'src/_caldavzap/dist/'),
    host: '0.0.0.0',
    port: 8079,
    hot: true,
    noInfo: true,
    overlay: {
      warnings: false,
      errors: true
    },
    historyApiFallback: true
    // headers: {
    //   'Access-Control-Allow-Origin': '*'
    // }
  },
  devtool: false,
  performance: {
    hints: false
  },
  module: {
    rules: [{
      //   test: /\.jsx?$/,
      //   enforce: 'pre',
      //   use: 'standard-loader',
      //   exclude: [/node_modules/]
      // }, {
      test: [/\.js$/, /\.jsx$/],
      exclude: [/node_modules/, /caldavzap.bundle.app.js/],
      loader: 'babel-loader',
      options: {
        presets: [
          '@babel/preset-env',
          '@babel/preset-react'
        ],
        plugins: [
          '@babel/plugin-proposal-object-rest-spread',
          '@babel/plugin-proposal-class-properties',
          '@babel/plugin-transform-object-assign'
        ]
      }
    }, {
      test: /\.css$/,
      use: ['style-loader', 'css-loader']
    }, {
      test: /\.styl$/,
      use: ['style-loader', 'css-loader', 'stylus-loader']
    }, {
      test: /\.(jpg|png|svg)$/,
      loader: 'url-loader',
      options: {
        limit: 25000
      }
    }]
  },
  resolve: {
    extensions: ['.js', '.jsx']
  },
  plugins: [
    ...[], // generic plugins always present
    ...(isProduction
        ? [] // production specific plugins
        : [] // development specific plugins
    )
  ]
}
