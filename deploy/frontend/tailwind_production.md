# Tailwind CSS Production Build (Recommended)

Current app uses Tailwind CDN for simplicity. For production, switch to a compiled/minified build to reduce JS execution and unused CSS.

## Why
- Smaller payload
- Faster first render
- Better Core Web Vitals
- Less runtime JS than CDN compiler

## Suggested Setup

1. Initialize frontend toolchain
```bash
npm init -y
npm install -D tailwindcss @tailwindcss/cli postcss autoprefixer cssnano
npx tailwindcss init -p
```

2. Configure content scan (`tailwind.config.js`)
```js
module.exports = {
  content: [
    './app/templates/**/*.html',
    './app/static/js/**/*.js'
  ],
  theme: { extend: {} },
  darkMode: 'class',
  plugins: []
}
```

3. Create source CSS (`app/static/css/tailwind.input.css`)
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

4. Build minified CSS
```bash
npx tailwindcss -i ./app/static/css/tailwind.input.css -o ./app/static/css/tailwind.min.css --minify
```

5. Replace CDN script in `app/templates/base.html`
- Remove `https://cdn.tailwindcss.com`
- Link compiled CSS:
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/tailwind.min.css') }}">
```

## Extra Performance Actions
- Convert images to WebP/AVIF where possible
- Add `loading="lazy"` for non-critical images
- Keep scripts deferred
- Remove unused external assets
- Cache static assets aggressively in Nginx (`immutable`)
