// Node-only verification helper: compile the same JS modules used by Expo.
// SecureStore is the only platform boundary replaced by an in-memory session.
const fs = require('fs');
const path = require('path');
const { transformSync } = require('@babel/core');

module.exports = function sourceLoader(session) {
  const cache = new Map();
  function load(filename) {
    filename = path.resolve(filename);
    if (cache.has(filename)) return cache.get(filename).exports;
    const module = { exports: {} };
    cache.set(filename, module);
    const { code } = transformSync(fs.readFileSync(filename, 'utf8'), {
      filename, configFile: false, babelrc: false,
      plugins: ['@babel/plugin-transform-modules-commonjs'],
    });
    const localRequire = (name) => {
      if (name === './AuthSession' && session) return { AuthSession: session };
      if (name.startsWith('.')) return load(path.resolve(path.dirname(filename), `${name}.js`));
      return require(name);
    };
    new Function('require', 'module', 'exports', code)(localRequire, module, module.exports);
    return module.exports;
  }
  return load;
};
